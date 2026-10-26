"""Generate AI images for scenes with visual.source ai_image (and the stills behind ai_clip/avatar).

Free providers (config ai_image.order, default flux -> local -> pollinations):
  flux          Hugging Face Space FLUX.1-schnell, anonymous ZeroGPU quota (~2 GPU-min/day), ~10 s, best quality
  local         stable-diffusion.cpp + DreamShaper 8 LCM on this laptop (tools/local_image.py): unlimited, offline
  pollinations  no key, low-res + watermark (cropped); now often answers 402 after a few images
One provider per video keeps the look consistent: the first provider that works becomes "sticky",
and storyboard "image_provider" (or --provider) forces one. FACTORY_OFFLINE=1 skips remote providers.
visual.ref (+ visual.strength) = reference image for img2img on the local provider (character consistency).
The brand's image_style is appended to every prompt; a fixed seed helps consistency.

Usage:
  python tools/gen_image.py .tmp/videos/<run> [--only scene_id] [--provider local|flux|pollinations]
  python tools/gen_image.py --prompt "..." --out path.jpg [--aspect 9x16] [--seed 7] [--provider local]   (one-off)
Updates storyboard.json visual.resolved for ai_image scenes and writes visual.still for ai_clip/avatar.
"""
import argparse
import os
import sys
import time
import urllib.parse
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image

import hf_space
import local_image
from common import BRANDS, add_credit, brand, config, load_json, run_paths, save_json
from events import emit, rel

SIZES = {"9x16": (768, 1344), "4x5": (896, 1120), "1x1": (1024, 1024), "16x9": (1344, 768)}


def flux(space: str, prompt: str, w: int, h: int, seed: int, out: Path) -> Path:
    res = hf_space.call(space, "/infer", prompt=prompt, seed=seed, randomize_seed=False,
                        width=w, height=h, num_inference_steps=4)
    Image.open(hf_space.result_path(res)).convert("RGB").save(out, quality=94)
    return out


def pollinations(prompt: str, w: int, h: int, seed: int, out: Path) -> Path:
    cfg = config()["ai_image"]
    url = cfg["pollinations_url"].format(prompt=urllib.parse.quote(prompt))
    r = requests.get(url, params={"width": w, "height": h, "seed": seed, "nologo": "true",
                                  "model": cfg["pollinations_model"]}, timeout=180)
    if r.status_code in (402, 429):
        DISABLED.add("pollinations")  # paywalled / rate-limited: don't hammer it for the rest of the run
    r.raise_for_status()
    im = Image.open(BytesIO(r.content)).convert("RGB")
    im = im.crop((0, 0, im.width, int(im.height * 0.95)))  # drop the bottom watermark strip
    im.resize((w, int(w * im.height / im.width)), Image.LANCZOS).save(out, quality=94)
    return out


DISABLED: set[str] = set()


def generate(prompt: str, aspect: str, seed: int, out: Path, style: str = "", prefer: str = "",
             ref: Path | None = None, strength: float = 0.6) -> tuple[Path, str]:
    """Try providers in order (prefer first). Returns (path, provider)."""
    full = f"{prompt}. {style}".strip(". ") if style else prompt
    w, h = SIZES[aspect]
    out.parent.mkdir(parents=True, exist_ok=True)
    order = list(config()["ai_image"].get("order", ["flux", "local", "pollinations"]))
    if prefer:
        order = [prefer] + [o for o in order if o != prefer]
    if os.getenv("FACTORY_OFFLINE"):
        order = [o for o in order if o == "local"]
    errors = []
    for prov in order:
        if prov in DISABLED:
            continue
        try:
            if prov == "flux":
                for space in config()["ai_image"]["hf_spaces"]:
                    return flux(space, full, w, h, seed, out), "flux"
            elif prov == "local" and local_image.available():
                return local_image.generate(full, aspect, seed, out, ref, strength), "local"
            elif prov == "pollinations":
                return pollinations(full, w, h, seed, out), "pollinations"
        except Exception as e:
            errors.append(f"{prov}: {str(e)[:160]}")
            print(f"  ! {prov}: {str(e)[:160]}", file=sys.stderr)
            if prov == "flux" and "quota" in str(e).lower():
                DISABLED.add("flux")
    raise RuntimeError("; ".join(errors) or "no provider available")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run", type=Path, nargs="?")
    ap.add_argument("--only", default="")
    ap.add_argument("--prompt", default="")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--aspect", default="9x16", choices=list(SIZES))
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--provider", default="", choices=["", "flux", "local", "pollinations"],
                    help="force/prefer one provider (match earlier shots of the same video)")
    args = ap.parse_args()

    if args.prompt:
        path, used = generate(args.prompt, args.aspect, args.seed, args.out, prefer=args.provider)
        print(f"{path} via {used}")
        return

    p = run_paths(args.run)
    sb = load_json(p["storyboard"])
    kit = brand(sb["brand"])
    style = kit.get("image_style", "")
    aspect = sb["aspects"][0]
    n, sticky = 0, args.provider or sb.get("image_provider", "")
    for s in sb["scenes"]:
        v = s.get("visual", {})
        if v.get("source") not in ("ai_image", "ai_clip", "avatar") or (args.only and s["id"] != args.only):
            continue
        if v["source"] == "avatar":
            aspect_s, prompt = "1x1", f"{v['prompt']}, head and shoulders portrait, facing camera, neutral background"
        else:
            aspect_s, prompt = aspect, v["prompt"]
        out = p["public"] / "visuals" / f"{s['id']}_ai.jpg"
        emit(args.run, "progress", "images", scene=s["id"], prompt=prompt[:160], provider=sticky or "auto")
        t_img = time.time()
        ref = None
        if v.get("ref"):
            ref = Path(v["ref"]) if Path(v["ref"]).is_absolute() else BRANDS / sb["brand"] / v["ref"]
        try:
            path, used = generate(prompt, aspect_s, v.get("seed", kit.get("seed", 7)), out, style, sticky,
                                  ref if ref and ref.exists() else None, v.get("strength", 0.6))
            sticky = sticky or used
        except Exception as e:
            print(f"  ! {s['id']}: all image providers failed: {e}", file=sys.stderr)
            v.update(resolved=None, kind="none", fallback_used="motion_card")
            emit(args.run, "fallback", "images", scene=s["id"], to="motion_card", reason=str(e)[:160])
            continue
        rel = f"visuals/{path.name}"
        if v["source"] == "ai_image":
            v.update(resolved=rel, kind="image", fallback_used="" if used == "flux" else used)
        else:
            v["still"] = rel  # animate_image.py / make_avatar.py turn this into video
            if v.get("kind") != "video":
                v.update(resolved=rel, kind="image")
        add_credit(args.run, {"scene": s["id"], "type": "ai_image", "credit": f"AI-generated image ({used})",
                              "source": used})
        n += 1
        emit(args.run, "asset", "images", scene=s["id"], type="image", provider=used, path=rel(path, args.run),
             seconds=round(time.time() - t_img, 1))
        if used != "flux":
            emit(args.run, "fallback", "images", scene=s["id"], to=used, reason="free remote quota unavailable or offline")
        print(f"  image {s['id']} via {used}", flush=True)
    save_json(p["storyboard"], sb)
    print(f"ai images: {n}")


if __name__ == "__main__":
    main()
