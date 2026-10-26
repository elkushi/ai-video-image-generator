"""Download and check every local (free, offline) model the factory uses. Safe to re-run.

Everything goes to .tmp/models/ (gitignored, re-downloadable; ~2 GB):
  sdcpp/      stable-diffusion.cpp Vulkan build (MIT)                    -> tools/local_image.py
  sd/         DreamShaper 8 LCM q8 GGUF (OpenRAIL-M, commercial OK)      -> tools/local_image.py
  taesd/      TAESD tiny VAE decoder (MIT)                               -> fast decode
  realesrgan/ realesrgan-ncnn-vulkan + models (BSD)                      -> tools/upscale.py
  depth/      Depth-Anything-V2-Small ONNX (Apache-2.0)                  -> tools/depth_parallax.py
plus: rembg isnet model (~/.rembg), offline fonts Inter + Cairo (assets/fonts), Piper voices en/ar/ru,
and the generated SFX library (assets/sfx).

Usage:
  python tools/setup_local_models.py [--bench]
--bench times each tool on this machine (prints numbers to put in workflows/make_video.md).
"""
import argparse
import os
import subprocess
import sys
import time
import zipfile
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import ROOT

M = ROOT / ".tmp/models"
SDCPP_API = "https://api.github.com/repos/leejet/stable-diffusion.cpp/releases/latest"
FILES = {
    "sd/DreamShaper8_LCM_q8_0.gguf": ("https://huggingface.co/haven-ai-companion/dreamshaper8-lcm-gguf/resolve/main/DreamShaper8_LCM_q8_0.gguf", 1802206336),
    "taesd/taesd.safetensors": ("https://huggingface.co/madebyollin/taesd/resolve/main/diffusion_pytorch_model.safetensors", 0),
    "depth/depth_anything_v2_small.onnx": ("https://huggingface.co/onnx-community/depth-anything-v2-small/resolve/main/onnx/model.onnx", 0),
}
REALESRGAN_ZIP = "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-ubuntu.zip"


def fetch(url: str, dst: Path, size: int = 0) -> None:
    """Resumable download with retries (HF/GitHub connections drop on this network)."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and (not size or dst.stat().st_size == size):
        print(f"  ok   {dst.relative_to(M)}")
        return
    for attempt in range(6):
        have = dst.stat().st_size if dst.exists() else 0
        try:
            with requests.get(url, headers={"Range": f"bytes={have}-"} if have else {}, stream=True, timeout=60) as r:
                if r.status_code == 416:
                    break
                r.raise_for_status()
                with dst.open("ab" if have and r.status_code == 206 else "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
            if not size or dst.stat().st_size == size:
                break
        except requests.RequestException as e:
            print(f"  ! {dst.name} attempt {attempt + 1}: {str(e)[:100]}")
            time.sleep(3 * (attempt + 1))
    print(f"  got  {dst.relative_to(M)} ({dst.stat().st_size // 1_000_000} MB)")


def unzip(url: str, dst: Path, marker: str) -> None:
    if list(dst.rglob(marker)):
        print(f"  ok   {dst.name}/{marker}")
        return
    z = dst.with_suffix(".zip")
    fetch(url, z)
    with zipfile.ZipFile(z) as zf:
        zf.extractall(dst)
    z.unlink()
    for f in dst.rglob(marker):
        f.chmod(0o755)
    print(f"  got  {dst.name}/{marker}")


def sdcpp_url() -> str:
    rel = requests.get(SDCPP_API, timeout=30).json()
    for a in rel["assets"]:
        n = a["name"]
        if "Linux" in n and n.endswith("vulkan.zip"):
            return a["browser_download_url"]
    raise SystemExit("no Linux Vulkan build in the latest stable-diffusion.cpp release")


def bench() -> None:
    sys.path.insert(0, str(ROOT / "tools"))
    tmp = ROOT / ".tmp/bench"
    tmp.mkdir(parents=True, exist_ok=True)
    py = sys.executable
    t = time.time()
    subprocess.run([py, str(ROOT / "tools/local_image.py"), "--prompt", "a cup of tea on a wooden kitchen table, soft light",
                    "--out", str(tmp / "sd.jpg"), "--aspect", "9x16"], check=False)
    print(f"BENCH local image (incl. upscale): {time.time() - t:.0f}s")
    t = time.time()
    subprocess.run([py, str(ROOT / "tools/depth_parallax.py"), str(tmp / "sd.jpg"), str(tmp / "par.mp4"), "--seconds", "2"], check=False)
    print(f"BENCH depth parallax 2 s clip: {time.time() - t:.0f}s")
    t = time.time()
    from rembg import new_session, remove
    from PIL import Image
    remove(Image.open(tmp / "sd.jpg"), session=new_session("isnet-general-use")).save(tmp / "cut.png")
    print(f"BENCH rembg cut-out: {time.time() - t:.0f}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", action="store_true")
    args = ap.parse_args()
    print("local models ->", M)
    unzip(sdcpp_url() if not (M / "sdcpp/sd-cli").exists() else "", M / "sdcpp", "sd-cli")
    unzip(REALESRGAN_ZIP, M / "realesrgan", "realesrgan-ncnn-vulkan")
    for rel, (url, size) in FILES.items():
        fetch(url, M / rel, size)
    print("  offline fonts (assets/fonts):")
    from extract_brand import google_font
    for fam in ("Inter", "Cairo"):
        if not all((ROOT / f"assets/fonts/{fam}-{w}.ttf").exists() for w in ("400", "500", "600", "700", "800")):
            google_font(fam, ROOT / "assets/fonts")
        print(f"  ok   {fam}")
    print("  piper offline voices:")
    from make_voiceover import piper_model
    import json as _json
    for lang, spec in _json.loads((ROOT / "config/factory.json").read_text())["languages"].items():
        for key in ("piper", "piper_female"):
            if spec.get(key):
                print(f"  ok   {lang}: {piper_model(spec[key]).name}")
    print("  sfx library:")
    subprocess.run([sys.executable, str(ROOT / "tools/make_sfx.py")], check=True)
    print("  rembg model (~180 MB in ~/.rembg):")
    from rembg import new_session
    new_session("isnet-general-use")
    print("  ok   rembg isnet-general-use")
    try:
        out = subprocess.run(["vulkaninfo", "--summary"], capture_output=True, text=True).stdout
        gpus = [l.split("=")[1].strip() for l in out.splitlines() if "deviceName" in l]
        print(f"  vulkan devices: {gpus}  (order differs per tool: realesrgan sees the MX350 as device 1 = config local.vulkan_gpu)")
    except FileNotFoundError:
        print("  ! vulkaninfo not found; GPU tools will fall back to CPU")
    free = os.popen("free -m | awk '/Mem:/{print $7}'").read().strip()
    print(f"  available RAM: {free} MB (local image gen needs ~2 GB; close browsers/apps for speed)")
    if args.bench:
        bench()


if __name__ == "__main__":
    main()
