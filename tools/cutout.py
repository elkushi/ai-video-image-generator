"""Cut product photos out of their background (free, local rembg).

Writes <name>_cutout.png (transparent) next to each photo. ProductHero uses the cut-out version
automatically when the storyboard points at the original (it checks for *_cutout.png).

Usage:
  python tools/cutout.py brands/<slug>/assets/products/            # every jpg/png/webp in the folder
  python tools/cutout.py photo.jpg [--model birefnet-general-lite]  # harder edges (hair, glass); slower
"""
import argparse
from pathlib import Path

from PIL import Image

EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", type=Path)
    ap.add_argument("--model", default="isnet-general-use")
    args = ap.parse_args()
    from rembg import new_session, remove
    session = new_session(args.model)
    files = [args.path] if args.path.is_file() else sorted(p for p in args.path.iterdir() if p.suffix.lower() in EXTS)
    for f in files:
        if f.stem.endswith("_cutout"):
            continue
        out = f.with_name(f"{f.stem}_cutout.png")
        cut = remove(Image.open(f).convert("RGBA"), session=session)
        bbox = cut.getbbox()  # trim empty margins so the product fills the frame
        (cut.crop(bbox) if bbox else cut).save(out)
        print(out)


if __name__ == "__main__":
    main()
