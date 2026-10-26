"""Render a run with Remotion (CPU, free). Bundles once, renders each requested aspect ratio.

Usage:
  python tools/render.py .tmp/videos/<run> --preview          # first aspect at half scale (fast QA pass)
  python tools/render.py .tmp/videos/<run>                    # all storyboard aspects, full quality + cover
  python tools/render.py .tmp/videos/<run> --aspects 9x16,1x1 [--frames 0-120]
Writes <run>/renders/Video-<aspect>[.preview].mp4 (+ .cover.jpg on final renders).
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from common import STUDIO, config, load_json, run_paths
from events import emit, rel


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run", type=Path)
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--aspects", default="")
    ap.add_argument("--frames", default="", help="frame range for quick checks, e.g. 0-90")
    ap.add_argument("--cover-frame", type=int, default=-1, help="frame for the cover still (default: ~1.2s into the hook)")
    args = ap.parse_args()

    cfg = config()
    p = run_paths(args.run)
    sb = load_json(p["storyboard"])
    props = load_json(p["props"])
    aspects = args.aspects.split(",") if args.aspects else sb["aspects"]
    if args.preview and not args.aspects:
        aspects = aspects[:1]
    comps = ",".join(cfg["aspects"][a]["composition"] for a in aspects)
    cover = args.cover_frame if args.cover_frame >= 0 else min(props["totalFrames"] - 1, int(cfg["fps"] * 1.2))

    cmd = ["node", "render.mjs", "--props", str(p["props"].resolve()), "--public", str(p["public"].resolve()),
           "--out", str(p["renders"].resolve()), "--comps", comps,
           "--concurrency", str(cfg["render"]["concurrency"]), "--crf", str(cfg["render"]["crf"])]
    if args.preview:
        cmd += ["--scale", str(cfg["render"]["preview_scale"])]
    else:
        cmd += ["--cover", str(cover)]
    if args.frames:
        cmd += ["--frames", args.frames]
    p["renders"].mkdir(exist_ok=True)
    t = time.time()
    emit(args.run, "log", "render", aspects=aspects, preview=args.preview, frames=props["totalFrames"])
    proc = subprocess.Popen(cmd, cwd=STUDIO, stdout=subprocess.PIPE, text=True, bufsize=1)
    for line in proc.stdout:
        if not line.startswith("@@"):
            print(line, end="", flush=True)
            continue
        tag, _, body = line[2:].partition(" ")
        try:
            d = json.loads(body)
        except ValueError:
            continue
        if tag == "progress":
            done = d.get("renderedFrames") or 0
            fps_r = done / d["elapsed"] if d.get("elapsed") else 0
            total = props["totalFrames"] if not args.frames else done or 1
            eta = (total - done) / fps_r + 3 if fps_r and done < total else 0
            emit(args.run, "progress", "render", comp=d["comp"], pct=round(d["progress"] * 100, 1),
                 frame=done, total=total, fps=round(fps_r, 1), eta=round(eta), stage=d.get("stage"))
        elif tag == "start":
            emit(args.run, "progress", "render", comp=d["comp"], pct=0, frame=0, total=d["frames"],
                 size=[d["width"], d["height"]])
        elif tag == "bundle":
            emit(args.run, "log", "render", bundled=round(d["seconds"], 1))
        elif tag == "done":
            emit(args.run, "asset", "render", comp=d["comp"], type="video", path=rel(d["out"], args.run),
                 seconds=round(d["seconds"], 1))
        elif tag == "cover":
            emit(args.run, "asset", "render", comp=d["comp"], type="image", path=rel(d["out"], args.run))
    r = proc.wait()
    r = type("R", (), {"returncode": r})
    if r.returncode:
        sys.exit(f"render failed (exit {r.returncode})")
    print(f"render done in {time.time() - t:.0f}s -> {p['renders']}")


if __name__ == "__main__":
    main()
