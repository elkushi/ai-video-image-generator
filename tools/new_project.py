"""Create a run folder for one video and copy the brand kit into its public/ dir.

Usage:
  python tools/new_project.py --brand demo --title "Launch teaser" [--brief "free text"] [--lang en]
Creates .tmp/videos/<YYYY-MM-DD>_<brand>_<slug>[_<lang>]/ with:
  brief.md, public/brand/{logo,fonts,assets}/   (Remotion's public dir for this run)
Prints the run folder path.
"""
import argparse
import shutil
from datetime import date

from common import BRANDS, ROOT, RUNS, brand, run_paths, slugify


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--brief", default="", help="Brief text (topic, goal, CTA, must-say points)")
    ap.add_argument("--lang", default="", help="Suffix the folder with a language code (multi-language runs)")
    args = ap.parse_args()

    brand(args.brand)  # fail early if the kit is missing
    name = f"{date.today().isoformat()}_{args.brand}_{slugify(args.title)}" + (f"_{args.lang}" if args.lang else "")
    run = RUNS / name
    p = run_paths(run)
    p["public"].mkdir(parents=True, exist_ok=True)
    for d in ("renders", "qa"):
        p[d].mkdir(exist_ok=True)

    src = BRANDS / args.brand
    dst = p["public"] / "brand"
    for sub in ("logo", "fonts", "assets"):
        if (src / sub).exists():
            shutil.copytree(src / sub, dst / sub, dirs_exist_ok=True)
    shutil.copy(src / "brand.json", dst / "brand.json")
    # offline fallback fonts (Inter: Latin+Cyrillic, Cairo: Arabic), loaded by studio/src/lib/fonts.ts
    shutil.copytree(ROOT / "assets/fonts", p["public"] / "fonts", dirs_exist_ok=True)

    if args.brief and not p["brief"].exists():
        p["brief"].write_text(f"# {args.title}\n\n{args.brief}\n", encoding="utf-8")
    print(run)


if __name__ == "__main__":
    main()
