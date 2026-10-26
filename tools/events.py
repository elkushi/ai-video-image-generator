"""Structured progress events, so the Factory app (app/) can animate what the tools are doing.

Every tool calls emit(run, kind, node, **data). One JSON line is appended to <run>/events.jsonl, and,
when the app started the job (env FACTORY_JOB=<id>), also to .tmp/app/jobs/<id>/tool_events.jsonl
(the app can't know the run folder before Claude creates it). Emitting never raises.

kind: stage_start | stage_end | tool_start | tool_end | progress | asset | fallback | check | log
node: validate | voice | stock | images | clips | avatar | music | sfx | props | render | qa | deliver
"""
import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def emit(run, kind: str, node: str, **data) -> None:
    try:
        run = Path(run).resolve() if run else None
        line = json.dumps({"ts": round(time.time(), 3), "source": "tool", "kind": kind, "node": node,
                           "run": run.name if run else None, "data": data}, ensure_ascii=False, default=str)
        targets = []
        if run and run.is_dir():
            targets.append(run / "events.jsonl")
        job = os.environ.get("FACTORY_JOB")
        if job:
            d = ROOT / ".tmp/app/jobs" / job
            d.mkdir(parents=True, exist_ok=True)
            targets.append(d / "tool_events.jsonl")
        for t in targets:
            with open(t, "a", encoding="utf-8") as f:
                f.write(line + "\n")
    except Exception:
        pass


def rel(path, run) -> str:
    """Path relative to the repo root, for the app's file API."""
    try:
        return str(Path(path).resolve().relative_to(ROOT))
    except Exception:
        return str(path)
