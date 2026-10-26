"""Validate post.json (3 post variants) before anything is rendered. Render only on PASS.

Checks: JSON schema, brand kit exists, variant ids and angles distinct, required props per layout,
on-image text length, single = 1 slide / carousel = 3-10 slides, files exist, custom HTML is
self-contained (no scripts, no network URLs), copy present for each platform with platform limits,
brand rules (no "!" / emoji when the brand forbids them), and numbers that are not in profile.md.

Usage:
  python tools/validate_post.py .tmp/posts/<run>/post.json
Exit code 0 = PASS (warnings allowed), 1 = FAIL. Prints a report.
"""
import argparse
import re
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

from common import BRANDS, ROOT, load_json

REQUIRED = {"title": ["title"], "stat": ["value", "label"], "quote": ["quote"], "list": ["items"],
            "compare": ["before", "after"], "icons": ["items"], "photo": ["headline"], "screen": ["image"],
            "cta": ["headline"], "custom": ["html"]}
MAX_CHARS = {"title": 90, "headline": 90, "subtitle": 140, "sub": 140, "label": 80, "value": 9, "quote": 200,
             "kicker": 32, "caption": 140, "button": 28}
COPY_LIMIT = {"linkedin": 3000, "instagram": 2200, "facebook": 5000, "x": 280, "tiktok": 2200}
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿\U0001F000-\U0001F2FF]")
NUM = re.compile(r"\d[\d.,]*\s?(?:%|B\+|M\+|K\+|\+|x)?")


def texts(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if k not in ("image", "prompt", "icon", "css", "device", "align"):
                yield from texts(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from texts(v)


def norm_num(s: str) -> str:
    return re.sub(r"[\s,]", "", s).rstrip(".")


def validate(spec: dict) -> tuple[list[str], list[str]]:
    errors, warns = [], []
    schema = load_json(ROOT / "schemas/post.schema.json")
    for e in Draft202012Validator(schema).iter_errors(spec):
        errors.append(f"schema: {'/'.join(map(str, e.path)) or '(root)'}: {e.message}")
    if errors:
        return errors, warns
    slug = spec["brand"]
    if not (BRANDS / slug / "brand.json").exists():
        return [f"brand kit brands/{slug}/brand.json not found"], warns
    kit = load_json(BRANDS / slug / "brand.json")
    profile = (BRANDS / slug / "profile.md").read_text(encoding="utf-8") if (BRANDS / slug / "profile.md").exists() else ""
    known_nums = {norm_num(m) for m in NUM.findall(profile)}
    donts = " ".join(kit.get("rules", {}).get("dont", [])).lower() + " " + profile.lower()
    no_bang = "exclamation" in donts
    no_emoji = "emoji" in donts

    vs = spec["variants"]
    ids = [v["id"] for v in vs]
    if len(set(ids)) != len(ids):
        errors.append(f"variant ids repeat: {ids}")
    if len(vs) < 3:
        warns.append(f"only {len(vs)} variant(s); the user expects 3 to choose from")
    angles = [v["angle"].strip().lower() for v in vs]
    if len(set(angles)) != len(angles):
        errors.append("variants must take different angles")

    for v in vs:
        tag = f"variant {v['id']}"
        n = len(v["slides"])
        if v["format"] == "single" and n != 1:
            errors.append(f"{tag}: format single needs exactly 1 slide (has {n})")
        if v["format"] == "carousel" and not 3 <= n <= 10:
            errors.append(f"{tag}: carousel needs 3-10 slides (has {n})")
        for p in spec["platforms"]:
            body = v["copy"].get(p, "")
            if not body.strip():
                errors.append(f"{tag}: copy.{p} missing")
            elif len(body) > COPY_LIMIT.get(p, 5000):
                errors.append(f"{tag}: copy.{p} is {len(body)} chars (limit {COPY_LIMIT[p]})")
        if len(v["copy"].get("hashtags", [])) > 8:
            warns.append(f"{tag}: {len(v['copy']['hashtags'])} hashtags; 3-5 reads better on LinkedIn")
        if not v["copy"].get("alt", "").strip():
            errors.append(f"{tag}: copy.alt (image alt text) missing")
        for i, s in enumerate(v["slides"], 1):
            st = f"{tag} slide {i} ({s['layout']})"
            pr = s.get("props", {})
            for k in REQUIRED[s["layout"]]:
                if k == "headline" and s["layout"] == "photo" and (pr.get("headline") or pr.get("title")):
                    continue
                if not pr.get(k):
                    errors.append(f"{st}: missing props.{k}")
            for k, lim in MAX_CHARS.items():
                if isinstance(pr.get(k), str) and len(pr[k].replace("**", "")) > lim:
                    (errors if len(pr[k]) > lim * 1.3 else warns).append(f"{st}: {k} is {len(pr[k])} chars (aim <= {lim})")
            if s["layout"] in ("list", "icons"):
                items = pr.get("items", [])
                if not 2 <= len(items) <= 6:
                    errors.append(f"{st}: {len(items)} items (use 2-6)")
                for it in items:
                    t = it if isinstance(it, str) else it.get("text", it.get("label", ""))
                    if len(t) > 60:
                        warns.append(f"{st}: item too long ({len(t)} chars): {t[:40]}...")
            if s["layout"] == "photo" and not (pr.get("image") or pr.get("prompt")):
                errors.append(f"{st}: photo needs props.image or props.prompt")
            for key in ("image",):
                ref = pr.get(key)
                if ref and not any(c.is_file() for c in ([Path(ref)] if Path(ref).is_absolute() else [BRANDS / slug / ref, ROOT / ref])):
                    (warns if pr.get("prompt") else errors).append(f"{st}: file not found: {ref}")
            if s["layout"] == "custom":
                h = str(pr.get("html", "")) + str(pr.get("css", ""))
                if re.search(r"<script|on\w+\s*=", h, re.I):
                    errors.append(f"{st}: custom html must not contain scripts or event handlers")
                if re.search(r"https?://", h):
                    errors.append(f"{st}: custom html must not load network URLs (put files in the brand kit)")
            for t in texts(pr):
                if no_bang and "!" in t:
                    errors.append(f"{st}: brand forbids exclamation marks: {t[:50]}")
                if no_emoji and EMOJI.search(t):
                    errors.append(f"{st}: brand forbids emoji: {t[:50]}")
                for m in NUM.findall(t):
                    if norm_num(m) and norm_num(m) not in known_nums and not re.fullmatch(r"\d{1,2}", norm_num(m)):
                        warns.append(f"{st}: number '{m.strip()}' is not in profile.md; confirm it is an approved fact")
        for p, body in v["copy"].items():
            if isinstance(body, str):
                if no_bang and "!" in body:
                    errors.append(f"{tag}: copy.{p} has an exclamation mark (brand rule)")
                if no_emoji and EMOJI.search(body):
                    errors.append(f"{tag}: copy.{p} has emoji (brand rule)")
    return errors, warns


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("post", type=Path)
    args = ap.parse_args()
    errors, warns = validate(load_json(args.post))
    for w in warns:
        print(f"WARN  {w}")
    for e in errors:
        print(f"FAIL  {e}")
    print("PASS" if not errors else f"FAIL ({len(errors)} errors)")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
