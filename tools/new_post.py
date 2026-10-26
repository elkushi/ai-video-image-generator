"""Create a post run folder: .tmp/posts/<YYYY-MM-DD>_<brand>_<slug>-post/ with brief.md.

Usage:
  python tools/new_post.py --brand demo --topic "Plan your week in five minutes" [--brief "lines..."]
Prints the run folder path (relative to the repo root).
"""
import argparse
import datetime as dt
import sys

from common import BRANDS, ROOT, slugify
from events import emit, rel

POSTS = ROOT / ".tmp/posts"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--topic", required=True)
    ap.add_argument("--brief", default="")
    args = ap.parse_args()
    if not (BRANDS / args.brand / "brand.json").exists():
        sys.exit(f"no brand kit brands/{args.brand}/ (run workflows/onboard_brand.md first)")
    slug = (slugify(args.topic) or "post")[:40].strip("-")
    base = f"{dt.date.today():%Y-%m-%d}_{args.brand}_{slug}-post"
    run, i = POSTS / base, 2
    while run.exists() and (run / "post.json").exists():
        run = POSTS / f"{base}{i}"
        i += 1
    run.mkdir(parents=True, exist_ok=True)
    (run / "brief.md").write_text(f"# {args.topic}\n\nBrand: {args.brand}\n\n{args.brief}\n", encoding="utf-8")
    emit(run, "log", "intake", folder=rel(run, run), job_kind="post")
    print(rel(run, run))


if __name__ == "__main__":
    main()
