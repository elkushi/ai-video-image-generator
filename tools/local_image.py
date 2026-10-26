"""Generate images locally with stable-diffusion.cpp (free, unlimited, offline).

Model: DreamShaper 8 LCM (q8 GGUF, OpenRAIL-M, commercial use allowed) + TAESD tiny decoder,
6 LCM steps at a small base size, then tools/upscale.py (Real-ESRGAN on the MX350) to 1080+.
Character consistency: pass --init (a reference portrait, e.g. brands/<slug>/assets/characters/hero.png)
for img2img; lower --strength keeps more of the reference (0.45-0.65 works well).
Settings (backend, base size, steps) live in config/factory.json -> "local".

Usage:
  python tools/local_image.py --prompt "..." --out shot.jpg [--aspect 9x16] [--seed 11] [--init ref.png --strength 0.55]
As a module: generate(prompt, aspect, seed, out, init=None, strength=0.55) -> out
"""
import argparse
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from PIL import Image

from common import ROOT, config
from upscale import upscale

MODELS = ROOT / ".tmp/models"
NEGATIVE = "text, letters, watermark, logo, signature, deformed, distorted face, extra fingers, bad hands, blurry, lowres, jpeg artifacts"


SIZES_512 = {"9x16": (384, 672), "4x5": (448, 576), "1x1": (512, 512), "16x9": (672, 384)}


def base_size(aspect: str, base: int) -> tuple[int, int]:
    """Small multiple-of-8 canvas with the target aspect ratio (SD1.5 is trained around 512 px)."""
    w, h = SIZES_512[aspect]
    f = base / 512
    return round(w * f / 8) * 8, round(h * f / 8) * 8


def available() -> bool:
    cfg = config()["local"]
    return (MODELS / "sdcpp/sd-cli").exists() and (MODELS / cfg["sd_model"]).exists()


def generate(prompt: str, aspect: str, seed: int, out: Path, init: Path | None = None, strength: float = 0.55,
             min_side: int = 1080) -> Path:
    cfg = config()["local"]
    w, h = base_size(aspect, cfg["sd_base"])
    with tempfile.TemporaryDirectory() as td:
        raw = Path(td) / "raw.png"
        cmd = [str(MODELS / "sdcpp/sd-cli"), "-m", str(MODELS / cfg["sd_model"]), "-p", prompt, "-n", NEGATIVE,
               "--sampling-method", "lcm", "--steps", str(cfg["sd_steps"]), "--cfg-scale", str(cfg["sd_cfg"]),
               "-W", str(w), "-H", str(h), "-s", str(seed), "--backend", cfg["sd_backend"], "-t", str(os.cpu_count() or 4),
               "-o", str(raw)]
        if (MODELS / "taesd/taesd.safetensors").exists():
            cmd += ["--taesd", str(MODELS / "taesd/taesd.safetensors")]
        if init:
            ref = Path(td) / "init.png"
            Image.open(init).convert("RGB").resize((w, h), Image.LANCZOS).save(ref)
            cmd += ["-i", str(ref), "--strength", str(strength)]
        t = time.time()
        r = subprocess.run(cmd, capture_output=True, text=True, env={**os.environ, "LD_LIBRARY_PATH": str(MODELS / "sdcpp")})
        if r.returncode or not raw.exists():
            raise RuntimeError(f"sd-cli failed: {r.stderr[-400:] or r.stdout[-400:]}")
        print(f"  local sd {w}x{h} in {time.time() - t:.0f}s", file=sys.stderr, flush=True)
        out.parent.mkdir(parents=True, exist_ok=True)
        upscale(raw, out, min_side)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--aspect", default="9x16", choices=["9x16", "4x5", "1x1", "16x9"])
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--init", type=Path)
    ap.add_argument("--strength", type=float, default=0.55)
    args = ap.parse_args()
    print(generate(args.prompt, args.aspect, args.seed, args.out, args.init, args.strength))


if __name__ == "__main__":
    main()
