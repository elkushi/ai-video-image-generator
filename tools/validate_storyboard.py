"""Validate storyboard.json before any asset is fetched or rendered. Render only on PASS.

Checks: JSON schema, per-scene required props, speaking pace (words/second per language),
on-screen text length, hook length, file paths, CTA present for promo/event videos.

Usage:
  python tools/validate_storyboard.py .tmp/videos/<run>/storyboard.json
Exit code 0 = PASS (warnings allowed), 1 = FAIL. Prints a report.
"""
import argparse
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

from common import BRANDS, ROOT, config, load_json, plain_vo

REQUIRED_PROPS = {
    "KineticTitle": ["title"],
    "FeatureList": ["items"],
    "StatCounter": ["value", "label"],
    "BeforeAfter": ["before", "after"],
    "Quote": ["quote"],
    "EventCard": ["title", "date"],
    "CTAEndCard": ["headline"],
}
NEEDS_VISUAL = {"ProductHero", "ScreenDemo", "StockBroll", "StoryShot"}
MAX_TITLE_WORDS = {"9x16": 9, "1x1": 9, "4x5": 9, "16x9": 12}


def words(text: str) -> int:
    return len(text.split())


def validate(sb: dict) -> tuple[list[str], list[str]]:
    errors, warns = [], []
    schema = load_json(ROOT / "schemas/storyboard.schema.json")
    for e in Draft202012Validator(schema).iter_errors(sb):
        errors.append(f"schema: {'/'.join(map(str, e.path)) or '(root)'}: {e.message}")
    if errors:
        return errors, warns

    cfg = config()
    lang = cfg["languages"][sb["language"]]
    if not (BRANDS / sb["brand"] / "brand.json").exists():
        errors.append(f"brand kit brands/{sb['brand']}/brand.json not found")

    ids = [s["id"] for s in sb["scenes"]]
    if len(ids) != len(set(ids)):
        errors.append("scene ids must be unique")

    total_words, est_seconds = 0, 0.0
    max_title = min(MAX_TITLE_WORDS[a] for a in sb["aspects"])
    for i, s in enumerate(sb["scenes"]):
        tag = f"scene {s['id']} ({s['type']})"
        props = s.get("props", {})
        for key in REQUIRED_PROPS.get(s["type"], []):
            if key not in props:
                errors.append(f"{tag}: props.{key} is required")
        vis = s.get("visual", {"source": "none"})
        if s["type"] in NEEDS_VISUAL and vis["source"] == "none":
            errors.append(f"{tag}: needs a visual (source != none)")
        if vis["source"] in ("stock_video", "stock_photo") and not vis.get("query"):
            errors.append(f"{tag}: stock visual needs a query")
        if vis["source"] in ("ai_image", "ai_clip", "avatar") and not vis.get("prompt"):
            errors.append(f"{tag}: {vis['source']} visual needs a prompt")
        if vis["source"] in ("file", "screenshot") and vis.get("path"):
            p = Path(vis["path"])
            if not p.is_absolute():
                p = BRANDS / sb["brand"] / p
            if not p.exists():
                errors.append(f"{tag}: file not found: {p}")
        elif vis["source"] in ("file", "screenshot"):
            errors.append(f"{tag}: {vis['source']} visual needs a path")

        vo = plain_vo(s.get("vo", "")).strip()
        w = words(vo)
        total_words += w
        rate = 1 + int((sb.get("voice_rate") or "+0%").strip("%")) / 100  # faster voice_rate = shorter
        pauses = (vo.count("…") + vo.count("...")) * cfg.get("ellipsis_pause", 0.6)
        speech = (w / lang["typical_wps"]) / rate + pauses
        sec = max(speech + cfg["scene_pause"], s.get("min_seconds", 0), 0 if vo else cfg["silent_scene_seconds"])
        if i == 0 and sec > 4.5:
            warns.append(f"{tag}: hook runs ~{sec:.1f}s; cut words or ellipses so the first beat lands in ≤4 s")
        est_seconds += sec
        if s.get("min_seconds") and vo and w / s["min_seconds"] > lang["max_wps"] * 1.15:
            warns.append(f"{tag}: {w} words in {s['min_seconds']}s is faster than {lang['max_wps']} w/s")
        title = str(props.get("title", props.get("headline", "")))
        if words(title) > max_title:
            warns.append(f"{tag}: on-screen title has {words(title)} words (max {max_title} for {sb['aspects']})")
        if i == 0 and vo and w > 14:  # noqa: word cap is separate from the time check above
            warns.append(f"{tag}: hook VO is {w} words; keep the first line under ~14 words (≈3 s)")

    if sb["goal"] in ("promo", "event", "announcement") and sb["scenes"][-1]["type"] != "CTAEndCard":
        warns.append("last scene is not a CTAEndCard; promo/event videos should end on a clear CTA")
    if est_seconds > 90:
        warns.append(f"estimated length {est_seconds:.0f}s exceeds 90s; Reels/LinkedIn retention drops sharply")
    print(f"estimate: {len(sb['scenes'])} scenes, {total_words} words, ~{est_seconds:.0f}s")
    return errors, warns


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("storyboard", type=Path)
    args = ap.parse_args()
    errors, warns = validate(load_json(args.storyboard))
    for w in warns:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")
    print("FAIL" if errors else "PASS")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
