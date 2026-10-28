"""Copy an uploaded file into a brand kit.

The headless agent has no shell cp/mv (a shell copy could move a secret somewhere readable), so this is
the one way an upload gets into brands/<slug>/. It only copies from .tmp/app/uploads/ and only into the
kit folders below.

  python tools/keep_upload.py .tmp/app/uploads/<draft>/logo.svg <slug> logo
  python tools/keep_upload.py .tmp/app/uploads/<draft>/photo.jpg <slug> assets/people
"""
import argparse
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UPLOADS = ROOT / ".tmp/app/uploads"
BRANDS = ROOT / "brands"
KIT_DIRS = {"logo", "fonts", "assets/products", "assets/screens", "assets/people"}
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


def keep(src: str, slug: str, kind: str) -> Path:
    s = (ROOT / src).resolve()
    if not s.is_relative_to(UPLOADS.resolve()) or not s.is_file():
        raise ValueError(f"not an uploaded file: {src}")
    if not SLUG_RE.match(slug) or slug.startswith("_"):
        raise ValueError(f"bad brand slug: {slug}")
    if kind not in KIT_DIRS:
        raise ValueError(f"kit folder must be one of {sorted(KIT_DIRS)}")
    dest_dir = BRANDS / slug / kind
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / s.name
    shutil.copy2(s, dest)
    return dest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("slug")
    ap.add_argument("kind", help=", ".join(sorted(KIT_DIRS)))
    a = ap.parse_args()
    try:
        print(keep(a.src, a.slug, a.kind).relative_to(ROOT))
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
