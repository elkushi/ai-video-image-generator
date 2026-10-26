"""Turn stills into short AI video clips for scenes with visual.source ai_clip (short films, hero shots).

Free providers: Hugging Face ZeroGPU Spaces from config ai_clip.hf_spaces (Wan 2.2 fast, LTX-Video).
The still is visual.path (your own product photo, relative to the brand folder) or the image
gen_image.py made (visual.still). Anonymous quota is a few clips per day; HF_TOKEN raises it.
On failure (quota, offline, FACTORY_OFFLINE=1) the still becomes a local depth-parallax "2.5D camera
move" clip (tools/depth_parallax.py, fallback_used = "parallax"); if that fails too, Remotion animates
the still with a Ken Burns move (fallback_used = "ken_burns"). The video always renders.

Usage:
  python tools/animate_image.py .tmp/videos/<run> [--only scene_id] [--seconds 4]
Run gen_image.py first. Updates storyboard.json visual.resolved/kind.
"""
import argparse
import os
import sys
from pathlib import Path

import hf_space
from common import BRANDS, add_credit, config, load_json, run_paths, save_json
from events import emit, rel

NEG = "blurry, distorted, low quality, text, watermark, jittery, deformed hands, morphing"


def wan(space: str, img: Path, prompt: str, seconds: float, seed: int):
    return hf_space.call(space, "/generate_video", input_image=hf_space.file_arg(img), prompt=prompt, steps=6,
                         negative_prompt=NEG, duration_seconds=seconds, guidance_scale=1, guidance_scale_2=1,
                         seed=seed, randomize_seed=False)


def ltx(space: str, img: Path, prompt: str, seconds: float, seed: int):
    from PIL import Image
    w, h = Image.open(img).size
    scale = 768 / max(w, h)
    return hf_space.call(space, "/image_to_video", prompt=prompt, negative_prompt=NEG,
                         input_image_filepath=hf_space.file_arg(img), input_video_filepath=None,
                         height_ui=int(h * scale) // 32 * 32, width_ui=int(w * scale) // 32 * 32,
                         mode="image-to-video", duration_ui=seconds, ui_frames_to_use=9, seed_ui=seed,
                         randomize_seed=False, ui_guidance_scale=1, improve_texture_flag=True)


def animate(img: Path, prompt: str, seconds: float, seed: int, out: Path) -> str:
    if os.getenv("FACTORY_OFFLINE"):
        return ""
    for space in config()["ai_clip"]["hf_spaces"]:
        fn = ltx if "ltx" in space.lower() else wan
        try:
            hf_space.keep(fn(space, img, prompt, seconds, seed), out)
            return space
        except Exception as e:
            print(f"  ! {str(e)[:200]}", file=sys.stderr)
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run", type=Path)
    ap.add_argument("--only", default="")
    ap.add_argument("--seconds", type=float, default=0)
    args = ap.parse_args()

    p = run_paths(args.run)
    sb = load_json(p["storyboard"])
    seconds = args.seconds or config()["ai_clip"]["seconds"]
    ok = total = 0
    for s in sb["scenes"]:
        v = s.get("visual", {})
        if v.get("source") != "ai_clip" or (args.only and s["id"] != args.only):
            continue
        total += 1
        if v.get("path"):
            img = Path(v["path"]) if Path(v["path"]).is_absolute() else BRANDS / sb["brand"] / v["path"]
        elif v.get("still"):
            img = p["public"] / v["still"]
        else:
            print(f"  ! {s['id']}: no still (run gen_image.py first)", file=sys.stderr)
            continue
        out = p["public"] / "visuals" / f"{s['id']}_clip.mp4"
        motion = f"{v['prompt']}. Smooth cinematic camera motion, natural movement"
        used = animate(img, motion, seconds, v.get("seed", 7), out)
        if used:
            v.update(resolved=f"visuals/{out.name}", kind="video", fallback_used="")
            add_credit(args.run, {"scene": s["id"], "type": "ai_clip", "credit": f"AI-generated video ({used})",
                                  "source": used})
            ok += 1
            print(f"  clip {s['id']} via {used}", flush=True)
            emit(args.run, "asset", "clips", scene=s["id"], type="video", provider=used, path=rel(out, args.run))
        else:
            if not v.get("still") and img.exists():
                import shutil
                dst = p["public"] / "visuals" / f"{s['id']}_still{img.suffix}"
                shutil.copy(img, dst)
                v["still"] = f"visuals/{dst.name}"
            try:
                from depth_parallax import MOVES, parallax, size_for
                clip = p["public"] / "visuals" / f"{s['id']}_parallax.mp4"
                parallax(p["public"] / v["still"], clip, seconds, MOVES.get(v.get("motion", "zoom_in"), "push"),
                         size_for(sb["aspects"][0]))
                v.update(resolved=f"visuals/{clip.name}", kind="video", fallback_used="parallax")
                print(f"  clip {s['id']} via local depth parallax", flush=True)
                emit(args.run, "fallback", "clips", scene=s["id"], to="parallax", reason="no free AI video quota")
                emit(args.run, "asset", "clips", scene=s["id"], type="video", provider="parallax", path=rel(clip, args.run))
            except Exception as e:
                print(f"  ! parallax {s['id']}: {e}", file=sys.stderr)
                v.update(resolved=v.get("still"), kind="image", fallback_used="ken_burns")
                emit(args.run, "fallback", "clips", scene=s["id"], to="ken_burns", reason=str(e)[:160])
    save_json(p["storyboard"], sb)
    print(f"ai clips: {ok}/{total} via HF (rest: local depth parallax, else Ken Burns)")


if __name__ == "__main__":
    main()
