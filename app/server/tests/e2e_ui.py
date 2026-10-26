"""Browser smoke test of the Factory web app (Playwright, Chromium).

Loads every page at desktop and phone width, fails on console errors / failed API calls, checks the post
features (gallery post card + detail, brand forms, Create post mode) and saves screenshots to .tmp/e2e/.
Needs a running server built from the current app/web/dist:
  FACTORY_PORT=8799 .venv/bin/python app/server/main.py &
  .venv/bin/python app/server/tests/e2e_ui.py [--base http://127.0.0.1:8799] [--post <output-name>]
Exit 0 = PASS.
"""
import argparse
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
SHOTS = ROOT / ".tmp/e2e"
WIDTHS = {"desktop": (1440, 900), "phone": (390, 844)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8799")
    ap.add_argument("--post", default="2026-10-26_demo_otp-uptime-post")
    ap.add_argument("--brand", default="demo")
    args = ap.parse_args()
    SHOTS.mkdir(parents=True, exist_ok=True)
    fails: list[str] = []

    pages = [("create", "/"), ("create-post", f"/?mode=post&brand={args.brand}"), ("runs", "/runs"),
             ("run-demo", "/runs/demo-replay"), ("gallery", "/gallery"), ("gallery-post", f"/gallery/{args.post}"),
             ("brands", "/brands"), ("brand", f"/brands/{args.brand}"), ("calendar", "/calendar"), ("stats", "/stats")]
    expect = {
        "create-post": ["Post", "Carousel"],
        "gallery": ["Carousel"],
        "gallery-post": ["Carousel PDF", "LinkedIn"],
        "brands": ["New brand from guide"],
        "brand": ["Make a post", "Update from brand guide"],
    }

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for wname, (w, h) in WIDTHS.items():
            ctx = browser.new_context(viewport={"width": w, "height": h})
            page = ctx.new_page()
            errors: list[str] = []
            warns: list[str] = []
            # resource 404s are reported by the response handler below (API = fail, /files = warn: .tmp is disposable)
            page.on("console", lambda m: errors.append(f"console {m.type}: {m.text}")
                    if m.type == "error" and not m.text.startswith("Failed to load resource") else None)
            page.on("response", lambda r: warns.append(f"missing file {r.url}") if r.status == 404 and "/files/" in r.url else None)
            page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
            page.on("response", lambda r: errors.append(f"HTTP {r.status} {r.url}")
                    if r.status >= 400 and "/api/" in r.url else None)
            for name, path in pages:
                errors.clear()
                page.goto(args.base + path, wait_until="networkidle")
                page.wait_for_timeout(1200)
                body = page.inner_text("body")
                for text in expect.get(name, []):
                    if text not in body:
                        fails.append(f"[{wname}] {name}: missing text '{text}'")
                offenders = page.evaluate("""() => {
                    const W = window.innerWidth, out = [];
                    const inScroller = (e) => { for (let p = e.parentElement; p && p.tagName !== 'MAIN'; p = p.parentElement) {
                        const o = getComputedStyle(p).overflowX; if (o === 'auto' || o === 'scroll' || o === 'hidden' || o === 'clip') return true; } return false; };
                    for (const e of document.querySelectorAll('main *')) {
                        const r = e.getBoundingClientRect();
                        if (r.width === 0 || r.height === 0 || r.right <= W + 2 || r.left >= W) continue;
                        if (inScroller(e)) continue;
                        out.push(`${e.tagName.toLowerCase()}.${e.className.toString().split(' ').slice(0, 3).join('.')} right=${Math.round(r.right)}`);
                    }
                    return out.slice(0, 3);
                }""")
                if offenders:
                    fails.append(f"[{wname}] {name}: content past the right edge: {offenders}")
                fails += [f"[{wname}] {name}: {e}" for e in errors]
                page.screenshot(path=str(SHOTS / f"{wname}_{name}.png"), full_page=True)
                print(f"ok  [{wname}] {name}" if not errors else f"ERR [{wname}] {name}: {errors[:2]}")
                for wmsg in warns:
                    print(f"WARN [{wname}] {name}: {wmsg}")
                warns.clear()
            ctx.close()
        browser.close()

    for f in fails:
        print("FAIL", f)
    print("PASS" if not fails else f"FAIL ({len(fails)})")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
