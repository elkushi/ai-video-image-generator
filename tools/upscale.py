"""Upscale stills locally (free): Real-ESRGAN ncnn-vulkan on the GPU, PIL Lanczos fallback.

Small tiles (-t 128) keep it inside the MX350's 2 GB VRAM. Models live in
.tmp/models/realesrgan/ (tools/setup_local_models.py downloads them).

Usage:
  python tools/upscale.py in.jpg out.jpg [--min-side 1080] [--model realesr-animevideov3|realesrgan-x4plus]
As a module: upscale(path_in, path_out, min_side=1080) -> (path, method)
"""
import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

from common import ROOT, config

RE_DIR = ROOT / ".tmp/models/realesrgan"


def esrgan_bin() -> Path | None:
    hits = list(RE_DIR.rglob("realesrgan-ncnn-vulkan"))
    return hits[0] if hits else None


def upscale(src: Path, dst: Path, min_side: int = 1080, model: str = "") -> tuple[Path, str]:
    im = Image.open(src).convert("RGB")
    short = min(im.size)
    if short >= min_side:
        if src != dst:
            im.save(dst, quality=94)
        return dst, "none"
    binary = esrgan_bin()
    if binary:
        local = config()["local"]
        scale = 2 if short * 2 >= min_side else (3 if short * 3 >= min_side else 4)
        mdl = model or local["upscale_model"]  # animevideov3: ~8 s for 768px x2 on the MX350; x4plus: ~200 s
        with tempfile.TemporaryDirectory() as td:
            tin, tout = Path(td) / "in.png", Path(td) / "out.png"
            im.save(tin)
            binary.chmod(0o755)
            r = subprocess.run([str(binary), "-i", str(tin), "-o", str(tout), "-n", mdl, "-s", str(scale),
                                "-t", "128", "-g", str(local["vulkan_gpu"]), "-m", str(binary.parent / "models")], capture_output=True, text=True)
            if r.returncode == 0 and tout.exists():
                up = Image.open(tout).convert("RGB")
                f = min_side / min(up.size)
                if f < 1:
                    up = up.resize((round(up.width * f), round(up.height * f)), Image.LANCZOS)
                up.save(dst, quality=94)
                return dst, f"realesrgan-x{scale}"
            print(f"  ! realesrgan failed: {r.stderr[-200:]}", file=sys.stderr)
    f = min_side / short
    im.resize((round(im.width * f), round(im.height * f)), Image.LANCZOS).save(dst, quality=94)
    return dst, "lanczos"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", type=Path)
    ap.add_argument("dst", type=Path)
    ap.add_argument("--min-side", type=int, default=1080)
    ap.add_argument("--model", default="", help="default config local.upscale_model")
    args = ap.parse_args()
    path, how = upscale(args.src, args.dst, args.min_side, args.model)
    print(f"{path} via {how}")


if __name__ == "__main__":
    main()
