"""Draft a brand kit for a new client: brands/<slug>/{brand.json, profile.md, logo/, fonts/, assets/}.

Sources (all free, any combination):
  --logo path        copied to logo/; dominant non-neutral colours become the palette
  --url  website     Playwright reads the live CSS (button/link/heading colours, font families),
                     takes a screenshot to assets/screens/ and saves the page text to .tmp for the profile
  --font  "Name"     downloads that Google Font (weights 400-800) into fonts/ (free, licence OFL)
  --primary/--secondary/--dark hex   explicit overrides from brand guidelines
Never overwrites an existing brand.json unless --force. Review and edit the draft afterwards
(workflows/onboard_brand.md).

Usage:
  python tools/extract_brand.py --slug acme --name "Acme" [--logo ~/Downloads/logo.png] [--url https://acme.com]
         [--font Montserrat] [--primary "#FF5A1F"] [--force]
"""
import argparse
import colorsys
import json
import re
import shutil
from collections import Counter
from pathlib import Path

import numpy as np
import requests
from PIL import Image

from common import BRANDS, ROOT, save_json

WEIGHTS = ["400", "500", "600", "700", "800"]


def hexc(rgb) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb[:3])


def lum(h: str) -> float:
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def sat(h: str) -> float:
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return colorsys.rgb_to_hls(r, g, b)[2]


def logo_palette(path: Path) -> list[str]:
    if path.suffix.lower() == ".svg":
        found = re.findall(r"#[0-9a-fA-F]{6}\b", path.read_text(errors="ignore"))
        return [c.upper() for c, _ in Counter(found).most_common(6)]
    im = Image.open(path).convert("RGBA")
    im.thumbnail((200, 200))
    px = np.asarray(im).reshape(-1, 4)
    px = px[px[:, 3] > 200][:, :3]
    q = Image.fromarray(px.reshape(1, -1, 3).astype("uint8"), "RGB")
    pal = np.asarray(q.quantize(colors=8).convert("RGB")).reshape(-1, 3)
    counts = Counter(map(tuple, pal))
    return [hexc(c) for c, _ in counts.most_common(8)]


def css_colors(parse: str) -> list[str]:
    out = []
    for m in re.findall(r"rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)", parse):
        if m[3] and float(m[3]) < 0.5:
            continue
        out.append(hexc(tuple(int(v) for v in m[:3])))
    return out


def scan_site(url: str, slug: str) -> dict:
    from playwright.sync_api import sync_playwright
    js = """() => {
      const pick = (sel, prop) => [...document.querySelectorAll(sel)].slice(0, 40).map(e => getComputedStyle(e)[prop]);
      return {
        buttons: pick('button, a[class*=btn], a[class*=button], [class*=cta]', 'backgroundColor'),
        links: pick('a', 'color'),
        headings: pick('h1, h2', 'color'),
        hfont: pick('h1, h2', 'fontFamily').slice(0, 3),
        bfont: pick('p, body', 'fontFamily').slice(0, 3),
        text: document.body.innerText.slice(0, 8000),
        title: document.title,
        desc: (document.querySelector('meta[name=description]') || {}).content || ''
      };
    }"""
    shots = BRANDS / slug / "assets/screens"
    shots.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        page = b.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=2)
        page.goto(url, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(2000)
        data = page.evaluate(js)
        page.screenshot(path=str(shots / "home_desktop.png"))
        b.close()
    (ROOT / ".tmp").mkdir(exist_ok=True)
    (ROOT / ".tmp" / f"site_{slug}.txt").write_text(f"{data['title']}\n{data['desc']}\n\n{data['text']}", encoding="utf-8")
    return data


def google_font(name: str, dst: Path) -> dict:
    """Download a Google Font (OFL) per weight; flaky connections are retried, failed weights skipped."""
    dst.mkdir(parents=True, exist_ok=True)
    files = {}
    for w in WEIGHTS:
        for attempt in range(3):
            try:
                css = requests.get("https://fonts.googleapis.com/css2", params={"family": f"{name}:wght@{w}"}, timeout=30)
                m = re.search(r"url\((https://[^)]+)\)", css.text) if css.status_code == 200 else None
                if not m:
                    break  # family or weight doesn't exist
                path = dst / f"{name.replace(' ', '')}-{w}.{m.group(1).rsplit('.', 1)[-1]}"
                path.write_bytes(requests.get(m.group(1), timeout=60).content)
                files[w] = f"fonts/{path.name}"
                break
            except requests.RequestException as e:
                print(f"  ! font {name} {w} attempt {attempt + 1}: {str(e)[:120]}")
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--logo", type=Path)
    ap.add_argument("--logo-dark", type=Path, help="logo version for dark backgrounds (white/reversed)")
    ap.add_argument("--url", default="")
    ap.add_argument("--font", default="", help="Google Font family for headings and body")
    ap.add_argument("--primary", default="")
    ap.add_argument("--secondary", default="")
    ap.add_argument("--dark", default="")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    kit = BRANDS / args.slug
    if (kit / "brand.json").exists() and not args.force:
        raise SystemExit(f"{kit}/brand.json exists (use --force to redraft)")
    shutil.copytree(BRANDS / "_template", kit, dirs_exist_ok=True)
    for f in kit.rglob(".gitkeep"):
        f.unlink()

    candidates, notes = [], []
    logo = {}
    if args.logo:
        dst = kit / "logo" / args.logo.name
        shutil.copy(args.logo, dst)
        logo["on_light"] = f"logo/{dst.name}"
        candidates += logo_palette(args.logo)
    if args.logo_dark:
        dst = kit / "logo" / args.logo_dark.name
        shutil.copy(args.logo_dark, dst)
        logo["on_dark"] = f"logo/{dst.name}"
    site = {}
    if args.url:
        site = scan_site(args.url, args.slug)
        candidates = css_colors(" ".join(site["buttons"] + site["links"])) + candidates
        notes.append(f"site fonts: headings {set(site['hfont'])}, body {set(site['bfont'])}")
        notes.append(f"site text saved to .tmp/site_{args.slug}.txt (use it to write profile.md)")

    brandish = [c for c, _ in Counter(c for c in candidates if 0.15 < lum(c) < 0.85 and sat(c) > 0.25).most_common()]
    primary = args.primary or (brandish[0] if brandish else "#3366FF")
    secondary = args.secondary or (brandish[1] if len(brandish) > 1 else primary)
    darks = [c for c in candidates if lum(c) < 0.15]
    dark = args.dark or (darks[0] if darks else "#111827")

    font_family, files = "Inter", {}
    if args.font:
        files = google_font(args.font, kit / "fonts")
        font_family = args.font if files else "Inter"
        notes.append(f"downloaded {len(files)} weights of {args.font}" if files else f"Google Font '{args.font}' not found")
    heading_files = {w: f for w, f in files.items() if w in ("700", "800")}
    body_files = {w: f for w, f in files.items() if w in ("400", "500", "600")}

    brand = {
        "_source": f"Drafted by tools/extract_brand.py from {', '.join(filter(None, [str(args.logo or ''), args.url]))}. REVIEW ME.",
        "name": args.name, "slug": args.slug, "tagline": site.get("desc", "")[:90], "website": re.sub(r"^https?://(www\.)?", "", args.url).rstrip("/"),
        "handle": "",
        "colors": {"primary": primary, "secondary": secondary, "dark": dark, "light": "#F4F6FB", "accent": secondary,
                   "text_on_dark": "#FFFFFF", "text_on_light": dark, "muted": "#7A8499"},
        "fonts": {"heading": {"family": font_family, "files": heading_files}, "body": {"family": font_family, "files": body_files}},
        "logo": logo, "radius": 24, "motif": "tilted_squares", "theme_default": "dark",
        "image_style": "clean modern photography, soft natural light, minimal composition, no text, no logos",
        "voices": {"en": "en-US-AndrewNeural", "ar": "ar-EG-ShakirNeural", "ru": "ru-RU-DmitryNeural"},
        "voice_rate": "+4%", "music_moods": ["corporate", "upbeat"], "seed": 7,
        "rules": {"do": [], "dont": ["Invent numbers, clients or quotes"]},
    }
    save_json(kit / "brand.json", brand)
    print(json.dumps({"kit": str(kit), "palette_candidates": brandish[:6], "chosen": brand["colors"], "notes": notes}, indent=2))


if __name__ == "__main__":
    main()
