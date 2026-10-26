"""Render the post variants in <run>/post.json to PNG previews with HyperFrames.

Steps: validate -> AI photos for `photo` slides that have a prompt but no image (free providers via
gen_image.py; on failure the slide degrades to a title card) -> one HyperFrames project holding every
variant (<run>/hf/previews) -> `hyperframes snapshot` -> <run>/previews/<V>/slide_NN.png plus
<run>/previews/contact.jpg (all variants, for QA) and <run>/previews/index.json.
Then a design check (`hyperframes check`, one sample per slide: text overflow, WCAG contrast, lint/runtime
errors) is stored in previews/index.json "checks" (runs in parallel with the snapshot; never fails the render; --no-check skips it).
--motion also renders an animated MP4 per variant (<run>/previews/<V>/motion.mp4).

Usage:
  python tools/render_post.py .tmp/posts/<run> [--variant A] [--motion] [--no-images] [--no-check]
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import post_html
from common import ROOT, brand, load_json, save_json
from events import emit, rel
from validate_post import validate

HF_BIN = ROOT / "hyperframes/node_modules/.bin/hyperframes"
ENV = {**os.environ, "HYPERFRAMES_SKIP_SKILLS": "1", "HYPERFRAMES_NO_TELEMETRY": "1", "DO_NOT_TRACK": "1"}


def hf(*args, timeout=600) -> subprocess.CompletedProcess:
    run = lambda a, t: subprocess.run([str(HF_BIN), *map(str, a)], capture_output=True, text=True, env=ENV, timeout=t, cwd=ROOT)
    r = run(args, timeout)
    if r.returncode != 0 and "browser ensure" in (r.stdout + r.stderr):
        # a cached Chrome path went stale (e.g. a deleted download): re-resolve once and retry
        run(["browser", "ensure"], 600)
        r = run(args, timeout)
    return r


def ai_photos(run: Path, spec: dict) -> int:
    import gen_image  # imported lazily: pulls in the Space client
    kit = brand(spec["brand"])
    aspect = spec.get("aspect", "4x5")
    n = 0
    for v in spec["variants"]:
        for i, s in enumerate(v["slides"], 1):
            p = s.get("props", {})
            if s["layout"] != "photo" or not p.get("prompt") or (p.get("image") and (ROOT / p["image"]).exists()):
                continue
            out = run / "images" / f"{v['id']}_{i}.jpg"
            emit(run, "progress", "images", scene=f"{v['id']}{i}", prompt=p["prompt"][:160], provider="auto")
            t = time.time()
            try:
                path, used = gen_image.generate(p["prompt"], aspect, p.get("seed", kit.get("seed", 7)), out, kit.get("image_style", ""))
                p["image"] = rel(path, run)
                p["image_provider"] = used
                n += 1
                emit(run, "asset", "images", scene=f"{v['id']}{i}", path=rel(path, run), provider=used, seconds=round(time.time() - t, 1))
            except Exception as e:
                print(f"  ! {v['id']} slide {i}: no AI image ({e}); slide falls back to a title card", file=sys.stderr)
                emit(run, "fallback", "images", scene=f"{v['id']}{i}", to="title_card", reason=str(e)[:160])
    return n


def snapshot(proj: Path, times: list[float], out: Path) -> list[Path]:
    if out.exists():
        shutil.rmtree(out)
    r = hf("snapshot", proj, "--at", ",".join(f"{t:g}" for t in times), "--no-end", "-o", out)
    frames = sorted(out.glob("frame-*.png"), key=lambda f: int(f.name.split("-")[1]))
    if r.returncode != 0 or len(frames) != len(times):
        raise RuntimeError(f"hyperframes snapshot failed ({r.returncode}): {(r.stderr or r.stdout)[-800:]}")
    return frames


def contact_sheet(spec: dict, previews: dict, out: Path, per_row: int = 5) -> None:
    """All variants on one sheet: a label row per variant, slides wrapped at per_row."""
    th = 420
    blocks = []
    for v in spec["variants"]:
        ims = [Image.open(p).convert("RGB") for p in previews[v["id"]]]
        ims = [im.resize((int(im.width * th / im.height), th), Image.LANCZOS) for im in ims]
        blocks.append((v, [ims[i:i + per_row] for i in range(0, len(ims), per_row)]))
    width = max(sum(im.width + 12 for im in row) for _, rows in blocks for row in rows) + 24
    height = sum(52 + len(rows) * (th + 12) + 18 for _, rows in blocks) + 12
    sheet = Image.new("RGB", (max(width, 900), height), "#16181d")
    d = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype(str(ROOT / "assets/fonts/Inter-600.ttf"), 26)
    except OSError:
        font = ImageFont.load_default()
    y = 12
    for v, rows in blocks:
        d.text((14, y + 8), f"{v['id']}  {v['format']}  {v['angle'][:90]}", fill="#e8e8e8", font=font)
        y += 52
        for row in rows:
            x = 12
            for im in row:
                sheet.paste(im, (x, y))
                x += im.width + 12
            y += th + 12
        y += 18
    sheet.save(out, quality=88)


IGNORED_CODES = {"duplicate_media_discovery_risk", "nested_structure_needs_subcomposition"}


def design_check(run: Path, proj: Path, variants: list[dict], times: dict) -> dict:
    """`hyperframes check` sampled once per slide: lint/runtime errors, text overflow and WCAG contrast.
    Video-only "craft" findings (reading time per line) and decorative overflow (info level) are dropped.
    Never fails the render; the findings go to previews/index.json "checks" and a qa event."""
    t = time.time()
    where = {tt: (vid, i + 1) for vid, ts in times.items() for i, tt in enumerate(ts)}
    at = ",".join(f"{tt:g}" for tt in sorted(where))
    try:
        r = hf("check", proj, "--json", "--at", at, "--samples", "1", timeout=180)
        data = json.loads(r.stdout[r.stdout.index("{"):])
    except Exception as e:
        out = {"ok": None, "skipped": f"check unavailable: {str(e)[:160]}", "seconds": round(time.time() - t, 1), "issues": []}
        emit(run, "check", "qa", name="design_check", ok=True, skipped=out["skipped"])
        return out
    issues = []
    for section in ("lint", "runtime", "layout", "contrast"):
        for f in (data.get(section) or {}).get("findings", []):
            if f.get("severity") not in ("error", "warning") or f.get("code") in IGNORED_CODES:
                continue
            ft = f.get("time")
            vid, slide = where.get(min(where, key=lambda x: abs(x - ft)), (None, None)) if isinstance(ft, (int, float)) and where else (None, None)
            issues.append({"variant": vid, "slide": slide, "check": section, "code": f.get("code"), "severity": f["severity"],
                           "message": f.get("message", "")[:200], "text": (f.get("text") or "")[:80], "selector": f.get("selector", "")})
    out = {"ok": not any(i["severity"] == "error" for i in issues), "seconds": round(time.time() - t, 1),
           "contrast_checked": (data.get("contrast") or {}).get("checked"), "issues": issues}
    emit(run, "check", "qa", name="design_check", ok=out["ok"], issues=len(issues), seconds=out["seconds"],
         top=[f"{i['variant']}{i['slide']}: {i['message'][:90]}" for i in issues[:5]])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run", type=Path)
    ap.add_argument("--variant", default="all")
    ap.add_argument("--motion", action="store_true", help="also render an animated MP4 per variant")
    ap.add_argument("--no-images", action="store_true", help="skip AI photo generation")
    ap.add_argument("--no-check", action="store_true", help="skip the hyperframes design check (~3 s per slide)")
    args = ap.parse_args()
    run = args.run.resolve()
    spec_path = run / "post.json"
    spec = load_json(spec_path)

    t0 = time.time()
    emit(run, "stage_start", "validate", tool="validate_post")
    errors, warns = validate(spec)
    emit(run, "stage_end", "validate", ok=not errors, errors=errors[:8], warnings=warns[:8], seconds=round(time.time() - t0, 1))
    for w in warns:
        print(f"WARN  {w}")
    if errors:
        for e in errors:
            print(f"FAIL  {e}")
        sys.exit(1)

    if not args.no_images and any(s["layout"] == "photo" and s.get("props", {}).get("prompt")
                                  for v in spec["variants"] for s in v["slides"]):
        t = time.time()
        emit(run, "stage_start", "images", tool="gen_image")
        n = ai_photos(run, spec)
        save_json(spec_path, spec)
        emit(run, "stage_end", "images", ok=True, count=n, seconds=round(time.time() - t, 1))

    variants = [v for v in spec["variants"] if args.variant in ("all", v["id"])]
    t = time.time()
    total = sum(len(v["slides"]) for v in variants)
    emit(run, "stage_start", "render", tool="hyperframes", slides=total, variants=[v["id"] for v in variants])
    built = post_html.build(spec, variants, run / "hf/previews")
    flat = [tt for v in variants for tt in built["times"][v["id"]]]
    pool = ThreadPoolExecutor(max_workers=1)
    checking = None if args.no_check else pool.submit(design_check, run, built["dir"], variants, built["times"])
    try:
        frames = snapshot(built["dir"], flat, run / "hf/snap")
    except Exception as e:
        emit(run, "stage_end", "render", ok=False, error=str(e)[:300], seconds=round(time.time() - t, 1))
        print(e, file=sys.stderr)
        sys.exit(2)
    index = load_json(run / "previews/index.json") if (run / "previews/index.json").exists() else {}
    k = 0
    for v in variants:
        vdir = run / "previews" / v["id"]
        if vdir.exists():
            shutil.rmtree(vdir)
        vdir.mkdir(parents=True)
        paths = []
        for i in range(len(v["slides"])):
            dst = vdir / f"slide_{i + 1:02d}.png"
            shutil.move(frames[k], dst)
            k += 1
            paths.append(dst)
            emit(run, "asset", "render", variant=v["id"], slide=i + 1, path=rel(dst, run))
        index[v["id"]] = {"angle": v["angle"], "format": v["format"], "slides": [rel(p, run) for p in paths]}
    emit(run, "stage_end", "render", ok=True, slides=total, seconds=round(time.time() - t, 1))
    if checking:
        index["checks"] = checking.result()
        for i in index["checks"]["issues"]:
            print(f"CHECK {i['severity']:7} {i['variant']}{i['slide']} {i['check']}: {i['message']} [{i['text']}]")

    if args.motion:
        for v in variants:
            t = time.time()
            emit(run, "stage_start", "render", tool="hyperframes render", variant=v["id"], motion=True)
            b = post_html.build(spec, [v], run / "hf" / v["id"], motion=True)
            mp4 = run / "previews" / v["id"] / "motion.mp4"
            r = hf("render", b["dir"], "-o", mp4, "--quality", "delivery", "--workers", "2", "--quiet", timeout=1800)
            ok = r.returncode == 0 and mp4.exists()
            if ok:
                index[v["id"]]["motion"] = rel(mp4, run)
            emit(run, "stage_end", "render", ok=ok, variant=v["id"], motion=True, seconds=round(time.time() - t, 1),
                 error="" if ok else (r.stderr or r.stdout)[-300:])

    all_prev = {vid: [ROOT / p for p in d["slides"]] for vid, d in index.items() if vid in {v["id"] for v in spec["variants"]}}
    if len(all_prev) == len(spec["variants"]):
        contact_sheet(spec, all_prev, run / "previews/contact.jpg")
        index["contact"] = rel(run / "previews/contact.jpg", run)
    save_json(run / "previews/index.json", index)
    print(json.dumps(index, indent=2, ensure_ascii=False))
    print(f"rendered {total} slide(s) in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
