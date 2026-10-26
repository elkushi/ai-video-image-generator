"""Run the deterministic part of the factory for one run folder (after storyboard.json is written).

Stages (in order):
  validate  -> validate_storyboard.py (stops on FAIL)
  voice     -> make_voiceover.py
  assets    -> fetch_stock.py, gen_image.py, animate_image.py, make_avatar.py, pick_music.py (only what the storyboard needs)
  props     -> build_props.py
  preview   -> render.py --preview, then qa_frames.py
  final     -> render.py (all aspects), qa_frames.py, postprocess.py

Usage:
  python tools/run_video.py .tmp/videos/<run>                 # validate .. preview (default)
  python tools/run_video.py .tmp/videos/<run> --final         # validate .. final (skips preview)
  python tools/run_video.py .tmp/videos/<run> --from props --final   # resume after editing props/scenes
  python tools/run_video.py .tmp/videos/<run> --only final
Flags passed through: --engine piper (offline voice), --allow-ai-music.
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

from common import ROOT, load_json, run_paths
from events import emit

STAGES = ["validate", "voice", "assets", "props", "preview", "final"]


RUN: Path | None = None


def tool(name: str, *args) -> None:
    cmd = [sys.executable, str(ROOT / "tools" / name), *map(str, args)]
    print(f"\n$ {' '.join(cmd[1:])}", flush=True)
    t = time.time()
    emit(RUN, "tool_start", STAGE, tool=name)
    r = subprocess.run(cmd)
    emit(RUN, "tool_end", STAGE, tool=name, ok=not r.returncode, seconds=round(time.time() - t, 1))
    if r.returncode:
        emit(RUN, "stage_end", STAGE, ok=False, error=f"{name} exited {r.returncode}")
        sys.exit(f"stopped: {name} exited {r.returncode}")
    print(f"  ({time.time() - t:.0f}s)", flush=True)


STAGE = "validate"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run", type=Path)
    ap.add_argument("--final", action="store_true")
    ap.add_argument("--from", dest="start", default="validate", choices=STAGES)
    ap.add_argument("--only", default="", choices=[""] + STAGES)
    ap.add_argument("--engine", default="edge", choices=["edge", "piper"])
    ap.add_argument("--allow-ai-music", action="store_true")
    args = ap.parse_args()

    run = args.run
    p = run_paths(run)
    if not p["storyboard"].exists():
        sys.exit(f"{p['storyboard']} missing: write the storyboard first (workflows/make_video.md step 3)")
    stages = [args.only] if args.only else STAGES[STAGES.index(args.start):]
    stages = [s for s in stages if s != ("preview" if args.final else "final")]

    global RUN, STAGE
    RUN = run
    sb = load_json(p["storyboard"])
    emit(run, "log", "pipeline", stages=stages, final=args.final, aspects=sb.get("aspects"),
         scenes=len(sb.get("scenes", [])), language=sb.get("language"), title=sb.get("title"))
    t_all = time.time()
    for stage in stages:
        STAGE = {"assets": "assets", "preview": "render", "final": "render"}.get(stage, stage)
        t_stage = time.time()
        emit(run, "stage_start", stage)
        run_stage(stage, run, p, args)
        emit(run, "stage_end", stage, ok=True, seconds=round(time.time() - t_stage, 1))
    emit(run, "log", "pipeline", done=True, seconds=round(time.time() - t_all, 1))


def run_stage(stage: str, run: Path, p: dict, args) -> None:
    global STAGE
    if True:
        if stage == "validate":
            tool("validate_storyboard.py", p["storyboard"])
        elif stage == "voice":
            tool("make_voiceover.py", run, "--engine", args.engine)
        elif stage == "assets":
            sources = {s.get("visual", {}).get("source") for s in load_json(p["storyboard"])["scenes"]}
            if sources & {"stock_video", "stock_photo"}:
                STAGE = "stock"
                tool("fetch_stock.py", run)
            if sources & {"ai_image", "ai_clip", "avatar"}:
                STAGE = "images"
                tool("gen_image.py", run)
            if "ai_clip" in sources:
                STAGE = "clips"
                tool("animate_image.py", run)
            if "avatar" in sources:
                STAGE = "avatar"
                tool("make_avatar.py", run)
            STAGE = "music"
            tool("pick_music.py", run, *(["--allow-ai"] if args.allow_ai_music else []))
        elif stage == "props":
            tool("build_props.py", run)
        elif stage == "preview":
            STAGE = "render"
            tool("render.py", run, "--preview")
            STAGE = "qa"
            tool("qa_frames.py", run)
        elif stage == "final":
            STAGE = "render"
            tool("render.py", run)
            for f in p["renders"].glob("*.preview.mp4"):
                f.unlink()
            STAGE = "qa"
            tool("qa_frames.py", run)
            STAGE = "deliver"
            tool("postprocess.py", run)


if __name__ == "__main__":
    main()
