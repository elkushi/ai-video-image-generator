"""Call free Hugging Face Spaces (ZeroGPU) with retries. Used by the AI asset tools.

Anonymous calls work but share a small daily GPU quota; a free HF_TOKEN in .env raises it.
Spaces come and go: the lists live in config/factory.json so they can be swapped without code changes.
"""
import os
import shutil
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

from common import ROOT

load_dotenv(ROOT / ".env")
EXHAUSTED: set[str] = set()  # spaces that reported "quota exceeded" in this process; skip them


def client(space: str):
    from gradio_client import Client
    kw = {"httpx_kwargs": {"timeout": 120}, "verbose": False}
    if os.getenv("HF_TOKEN"):
        kw["token"] = os.getenv("HF_TOKEN")
    return Client(space, **kw)


def call(space: str, api_name: str, retries: int = 2, **params):
    """predict() with retries on network errors; raises the last error so callers can fall back."""
    if space in EXHAUSTED:
        raise RuntimeError(f"{space}: ZeroGPU quota already exhausted in this run")
    err = None
    for attempt in range(retries + 1):
        try:
            return client(space).predict(api_name=api_name, **params)
        except Exception as e:  # quota exceeded, space sleeping, SSL hiccup ...
            err = e
            msg = str(e).lower()
            if "quota" in msg or "exceeded" in msg:
                EXHAUSTED.add(space)
                break  # retrying won't help today
            print(f"  ! {space} attempt {attempt + 1}: {str(e)[:160]}", file=sys.stderr)
            time.sleep(4 * (attempt + 1))
    raise RuntimeError(f"{space}: {err}")


def file_arg(path: Path):
    from gradio_client import handle_file
    return handle_file(str(path))


def result_path(res) -> Path:
    """Gradio returns a path, a (path, x) tuple or {'video': path}; normalise to a Path."""
    if isinstance(res, (list, tuple)):
        res = res[0]
    if isinstance(res, dict):
        res = res.get("video") or res.get("path") or res.get("value")
    return Path(res)


def keep(res, dst: Path) -> Path:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(result_path(res), dst)
    return dst
