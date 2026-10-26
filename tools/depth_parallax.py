"""Turn a still into a short "2.5D camera move" clip, fully local and free.

Depth-Anything-V2-Small (ONNX, CPU, ~1-3 s) estimates depth; each output frame displaces
pixels by depth so near objects move more than far ones (parallax), with a gentle push-in.
This is the local replacement for AI image-to-video when no GPU quota is available.

Usage:
  python tools/depth_parallax.py in.jpg out.mp4 [--seconds 4] [--move push|orbit_left|orbit_right|rise] [--size 1080x1920]
  python tools/depth_parallax.py --run .tmp/videos/<run> [--only scene_id]   # all scenes that fell back to ken_burns
As a module: parallax(img, out, seconds, move, size) -> out
"""
import argparse
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

from common import ROOT, add_credit, config, load_json, run_paths, save_json

MODEL = ROOT / ".tmp/models/depth/depth_anything_v2_small.onnx"
MOVES = {"zoom_in": "push", "zoom_out": "pull", "pan_left": "orbit_left", "pan_right": "orbit_right",
         "pan_up": "rise", "pan_down": "rise", "static": "push"}
_session = None


def depth_map(im: Image.Image) -> np.ndarray:
    """0 = far, 1 = near, same size as im."""
    global _session
    import onnxruntime as ort
    if _session is None:
        _session = ort.InferenceSession(str(MODEL), providers=["CPUExecutionProvider"])
    side = 518  # model's native resolution (multiple of 14)
    x = np.asarray(im.convert("RGB").resize((side, side), Image.BICUBIC), dtype=np.float32) / 255
    x = (x - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]
    x = x.transpose(2, 0, 1)[None].astype(np.float32)
    d = _session.run(None, {_session.get_inputs()[0].name: x})[0][0]
    d = (d - d.min()) / (d.max() - d.min() + 1e-6)
    d = np.asarray(Image.fromarray((d * 255).astype(np.uint8)).resize(im.size, Image.BICUBIC), dtype=np.float32) / 255
    # soften edges so displacement doesn't tear around outlines
    from PIL import ImageFilter
    return np.asarray(Image.fromarray((d * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(6)), dtype=np.float32) / 255


def cover(im: Image.Image, w: int, h: int, margin: float) -> Image.Image:
    """Resize/crop to w x h plus a safety margin so displaced edges never show."""
    W, H = int(w * (1 + margin)), int(h * (1 + margin))
    f = max(W / im.width, H / im.height)
    im = im.resize((round(im.width * f), round(im.height * f)), Image.LANCZOS)
    l, t = (im.width - W) // 2, (im.height - H) // 2
    return im.crop((l, t, l + W, t + H))


def parallax(img: Path, out: Path, seconds: float = 4, move: str = "push", size: tuple[int, int] = (1080, 1920),
             fps: int = 30, strength: float = 0.035) -> Path:
    w, h = size
    margin = 0.12
    src = cover(Image.open(img).convert("RGB"), w, h, margin)
    arr = np.asarray(src, dtype=np.float32)
    depth = depth_map(src)
    H, W = depth.shape
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    cx, cy = W / 2, H / 2
    n = int(seconds * fps)
    ox0, oy0 = (W - w) / 2, (H - h) / 2
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{w}x{h}", "-r", str(fps), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                             "-crf", "18", "-preset", "veryfast", str(out)], stdin=subprocess.PIPE)
    for i in range(n):
        p = i / max(1, n - 1)
        e = p * p * (3 - 2 * p)  # smoothstep
        zoom = {"push": 1 + 0.06 * e, "pull": 1.06 - 0.06 * e}.get(move, 1 + 0.03 * e)
        dx = {"orbit_left": -1, "orbit_right": 1}.get(move, 0) * (e - 0.5) * 2 * strength * W
        dy = (-(e - 0.5) * 2 * strength * H) if move == "rise" else 0
        # near pixels (depth~1) move with the camera, far ones (depth~0) stay: sample the source inversely
        k = depth * 1.0
        sx = cx + (xx - cx) / (1 + (zoom - 1) * (0.4 + 0.6 * k)) - dx * k
        sy = cy + (yy - cy) / (1 + (zoom - 1) * (0.4 + 0.6 * k)) - dy * k
        # crop window inside the margin
        sx = sx[int(oy0):int(oy0) + h, int(ox0):int(ox0) + w]
        sy = sy[int(oy0):int(oy0) + h, int(ox0):int(ox0) + w]
        xi = np.clip(sx, 0, W - 1.001)
        yi = np.clip(sy, 0, H - 1.001)
        x0, y0 = xi.astype(np.int32), yi.astype(np.int32)
        fx, fy = (xi - x0)[..., None], (yi - y0)[..., None]
        a, b = arr[y0, x0], arr[y0, x0 + 1]
        c, d = arr[y0 + 1, x0], arr[y0 + 1, x0 + 1]
        frame = (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy
        proc.stdin.write(frame.astype(np.uint8).tobytes())
    proc.stdin.close()
    if proc.wait():
        raise RuntimeError("ffmpeg failed while encoding parallax clip")
    return out


def size_for(aspect: str) -> tuple[int, int]:
    a = config()["aspects"][aspect]
    return a["width"], a["height"]


def run_mode(run: Path, only: str) -> None:
    p = run_paths(run)
    sb = load_json(p["storyboard"])
    size = size_for(sb["aspects"][0])
    seconds = config()["ai_clip"]["seconds"]
    done = 0
    for s in sb["scenes"]:
        v = s.get("visual", {})
        if only and s["id"] != only:
            continue
        if v.get("source") not in ("ai_clip", "ai_image") or v.get("kind") != "image" or not v.get("resolved"):
            continue
        if v["source"] == "ai_image" and not only:
            continue  # by default only ai_clip scenes (that fell back to a still) get parallax
        out = p["public"] / "visuals" / f"{s['id']}_parallax.mp4"
        parallax(p["public"] / v["resolved"], out, seconds, MOVES.get(v.get("motion", "zoom_in"), "push"), size)
        v.update(resolved=f"visuals/{out.name}", kind="video", fallback_used="parallax")
        add_credit(run, {"scene": s["id"], "type": "ai_clip", "credit": "Depth-parallax animation (local)", "source": "depth-anything-v2-small"})
        done += 1
        print(f"  parallax {s['id']}", flush=True)
    save_json(p["storyboard"], sb)
    print(f"parallax clips: {done}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", type=Path, nargs="?")
    ap.add_argument("out", type=Path, nargs="?")
    ap.add_argument("--run", type=Path)
    ap.add_argument("--only", default="")
    ap.add_argument("--seconds", type=float, default=4)
    ap.add_argument("--move", default="push", choices=["push", "pull", "orbit_left", "orbit_right", "rise"])
    ap.add_argument("--size", default="1080x1920")
    args = ap.parse_args()
    if args.run:
        run_mode(args.run, args.only)
        return
    w, h = map(int, args.size.split("x"))
    print(parallax(args.src, args.out, args.seconds, args.move, (w, h)))


if __name__ == "__main__":
    main()
