"""Deliver the picked post variant: output/<run-name>/ gets
  slide_01.png ... (1080 px PNGs), cover.jpg, carousel.pdf (carousels: LinkedIn document post),
  motion.mp4 (if rendered), post.md (copy per platform, alt text, posting time), post.json (picked=V),
  brief.md, credits.txt.
Deterministic: no AI here. Copy edits from the user (JSON {"linkedin": "...", "alt": "..."}) override the variant's copy.

Usage:
  python tools/deliver_post.py .tmp/posts/<run> --pick B [--copy-edits edits.json]
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

from PIL import Image

from common import ROOT, brand, load_json, save_json
from events import emit, rel

TITLES = {"linkedin": "LinkedIn", "instagram": "Instagram", "facebook": "Facebook", "x": "X", "tiktok": "TikTok"}


def post_md(spec: dict, v: dict, ai_used: list[str]) -> str:
    c = v["copy"]
    tags = " ".join(h if h.startswith("#") else f"#{h}" for h in c.get("hashtags", []))
    out = []
    for p in spec["platforms"]:
        body = c.get(p, "").strip()
        if tags and tags not in body and p in ("linkedin", "instagram"):
            body += f"\n\n{tags}"
        out.append(f"## {TITLES.get(p, p)}\n\n{body}\n")
    out.append(f"## Alt text\n\n{c.get('alt', '').strip()}\n")
    if spec.get("posting_time"):
        out.append(f"## Suggested posting time\n\n{spec['posting_time']}\n")
    if v["format"] == "carousel":
        out.append("## How to post\n\nLinkedIn: upload carousel.pdf as a document post (add a title). "
                   "Instagram: upload the slide PNGs in order as one carousel.\n")
    if ai_used:
        out.append(f"## Disclosure\n\nThe photo on slide(s) {', '.join(ai_used)} is AI-generated. "
                   "LinkedIn and Instagram may label it; keep the label.\n")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run", type=Path)
    ap.add_argument("--pick", required=True)
    ap.add_argument("--copy-edits", type=Path)
    args = ap.parse_args()
    run = args.run.resolve()
    spec = load_json(run / "post.json")
    v = next((x for x in spec["variants"] if x["id"] == args.pick), None)
    if not v:
        sys.exit(f"variant {args.pick} not in post.json")
    if args.copy_edits:
        v["copy"].update({k: val for k, val in load_json(args.copy_edits).items() if isinstance(val, (str, list))})
    index = load_json(run / "previews/index.json")
    slides = [ROOT / p for p in index.get(v["id"], {}).get("slides", [])]
    if not slides or not all(p.exists() for p in slides):
        sys.exit(f"no rendered previews for {v['id']}; run tools/render_post.py first")

    emit(run, "stage_start", "deliver", tool="deliver_post", pick=v["id"])
    out = ROOT / "output" / run.name
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    pngs = []
    for i, src in enumerate(slides, 1):
        dst = out / f"slide_{i:02d}.png"
        shutil.copy(src, dst)
        pngs.append(dst)
    Image.open(pngs[0]).convert("RGB").save(out / "cover.jpg", quality=92)
    if v["format"] == "carousel":
        ims = [Image.open(p).convert("RGB") for p in pngs]
        ims[0].save(out / "carousel.pdf", save_all=True, append_images=ims[1:], resolution=144)
    motion = run / "previews" / v["id"] / "motion.mp4"
    if motion.exists():
        shutil.copy(motion, out / "motion.mp4")

    ai_used = [str(i) for i, s in enumerate(v["slides"], 1) if s["layout"] == "photo" and s.get("props", {}).get("image_provider")]
    (out / "post.md").write_text(post_md(spec, v, ai_used), encoding="utf-8")
    picked = {**spec, "picked": v["id"], "variants": [v],
              "alternatives": [{"id": x["id"], "angle": x["angle"]} for x in spec["variants"] if x["id"] != v["id"]]}
    save_json(out / "post.json", picked)
    spec["picked"] = v["id"]
    save_json(run / "post.json", spec)
    if (run / "brief.md").exists():
        shutil.copy(run / "brief.md", out / "brief.md")
    kit = brand(spec["brand"])
    fonts = sorted({f.get("family", "") for f in (kit.get("fonts") or {}).values() if isinstance(f, dict)})
    credits = [f"Design: HyperFrames (Apache-2.0) with the {kit.get('name', spec['brand'])} brand kit",
               f"Fonts: {', '.join(fonts)} (brand kit); fallbacks Inter and Cairo (OFL)"]
    for i, s in enumerate(v["slides"], 1):
        prov = s.get("props", {}).get("image_provider")
        if prov:
            credits.append(f"Slide {i} photo: AI-generated ({prov})")
    (out / "credits.txt").write_text("\n".join(credits) + "\n", encoding="utf-8")
    emit(run, "stage_end", "deliver", ok=True, folder=rel(out, run), files=[p.name for p in sorted(out.iterdir())])
    print(json.dumps({"folder": rel(out, run), "files": [p.name for p in sorted(out.iterdir())]}, indent=2))


if __name__ == "__main__":
    main()
