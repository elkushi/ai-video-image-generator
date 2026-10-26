"""Capture product screenshots / scroll videos of a website or web app (free, local Playwright).

Use for SaaS and app brands: the shots go into brands/<slug>/assets/screens/ and are referenced
from storyboards as {"source": "screenshot", "path": "assets/screens/<file>"}.
Logged-in pages: pass --storage state.json (export once with `playwright codegen --save-storage`).

Usage:
  python tools/capture_screens.py --brand acme --url https://acme.example [--url https://acme.example/pricing]
         [--device phone|desktop|both] [--full] [--scroll-video] [--wait 2500] [--storage state.json]
Prints the saved file paths.
"""
import argparse
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

from common import BRANDS

DEVICES = {
    "phone": {"viewport": {"width": 430, "height": 932}, "device_scale_factor": 3, "is_mobile": True, "has_touch": True},
    "desktop": {"viewport": {"width": 1440, "height": 900}, "device_scale_factor": 2},
}
HIDE = "[id*=cookie],[class*=cookie],[id*=consent],[class*=consent],[class*=gdpr],#onetrust-banner-sdk{display:none!important}"


def name_for(url: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", re.sub(r"^https?://(www\.)?", "", url.lower())).strip("-")[:60] or "page"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--url", action="append", required=True)
    ap.add_argument("--device", default="both", choices=["phone", "desktop", "both"])
    ap.add_argument("--full", action="store_true", help="full-page screenshot (tall image for scrolling ScreenDemo)")
    ap.add_argument("--scroll-video", action="store_true", help="also record a smooth scroll video (.webm -> .mp4)")
    ap.add_argument("--wait", type=int, default=2500, help="ms to wait after load for animations")
    ap.add_argument("--storage", default="", help="Playwright storage state for logged-in pages")
    args = ap.parse_args()

    out = BRANDS / args.brand / "assets/screens"
    out.mkdir(parents=True, exist_ok=True)
    devices = ["phone", "desktop"] if args.device == "both" else [args.device]
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for dev in devices:
            opts = dict(DEVICES[dev])
            if args.storage:
                opts["storage_state"] = args.storage
            if args.scroll_video:
                opts["record_video_dir"] = str(out / "_rec")
                opts["record_video_size"] = opts["viewport"]
            ctx = browser.new_context(**opts)
            for url in args.url:
                page = ctx.new_page()
                page.goto(url, wait_until="networkidle", timeout=60000)
                page.add_style_tag(content=HIDE)
                page.wait_for_timeout(args.wait)
                path = out / f"{name_for(url)}_{dev}{'_full' if args.full else ''}.png"
                page.screenshot(path=str(path), full_page=args.full)
                print(path)
                if args.scroll_video:
                    height = page.evaluate("document.body.scrollHeight")
                    for y in range(0, height, 12):
                        page.evaluate(f"window.scrollTo(0, {y})")
                        page.wait_for_timeout(16)
                    page.wait_for_timeout(500)
                    video = page.video
                    page.close()
                    if video:
                        webm = Path(video.path())
                        mp4 = out / f"{name_for(url)}_{dev}_scroll.mp4"
                        import subprocess
                        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(webm), "-c:v", "libx264",
                                        "-pix_fmt", "yuv420p", "-crf", "20", str(mp4)], check=True)
                        webm.unlink()
                        print(mp4)
                else:
                    page.close()
            ctx.close()
        browser.close()


if __name__ == "__main__":
    main()
