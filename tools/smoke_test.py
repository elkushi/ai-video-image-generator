"""Regression check for the whole factory: render tiny videos end to end and assert QA passes.

Run it after changing any tool, scene, config or dependency. It works offline: FACTORY_OFFLINE=1 is set and
the Piper voice is used unless you pass --online, which tests edge-tts.

Cases (demo brand, motion-graphics scenes, ~8 s each):
  en 1x1 dark  ·  ar 9x16 brand (RTL, portrait safe zones)  ·  ru 16x9 light
Stages: validate -> voice -> assets -> props -> render -> qa_frames (no delivery to output/).
Must pass: duration, audio, black_frames, vo_match, vo_cut (loudness is fixed later by postprocess).
Post case (always, also in --quick): a 3-variant demo post (single stat, 3-slide carousel, single quote)
-> validate_post -> render_post (HyperFrames, no AI images, design check) -> deliver_post --pick B; asserts
1080x1350 PNGs per slide, carousel.pdf with 3 pages, post.md/post.json/cover.jpg, and no design-check errors.
The delivered smoke-test folder is removed afterwards.

Usage:
  python tools/smoke_test.py --quick           # ar 9x16 only, half-scale preview (~2 min)
  python tools/smoke_test.py                   # all three cases, full quality
  python tools/smoke_test.py --langs en,ru [--online] [--with-ai]
  python tools/smoke_test.py --post-only       # just the HyperFrames post case (~1 min)
  python tools/smoke_test.py --no-post         # skip the post case
--with-ai adds a StoryShot with a local sd.cpp image (slow: ~10 min on a modest laptop).
Exit code 0 = all passed, 1 = something failed (details printed and in each run's qa/qa_*.json).
"""
import argparse
import os
import shutil
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

from common import ROOT, RUNS, load_json, run_paths, save_json

MUST_PASS = {"duration", "audio", "black_frames", "vo_match", "vo_cut"}

CASES = {
    "en": {"aspect": "1x1", "theme": "dark", "scenes": [
        {"id": "hook", "type": "KineticTitle", "vo": "This is a quick factory check.",
         "props": {"kicker": "Smoke test", "title": "Every scene renders", "highlight": ["renders"]}},
        {"id": "list", "type": "FeatureList", "vo": "Voice, captions and music all work.",
         "props": {"title": "What we check", "items": [{"text": "Voice", "icon": "1"}, {"text": "Captions", "icon": "2"}, {"text": "Music", "icon": "3"}]}},
        {"id": "stat", "type": "StatCounter", "vo": "Three languages, one pipeline.",
         "props": {"value": 3, "label": "languages"}},
        {"id": "cta", "type": "CTAEndCard", "vo": "Follow Margin Notes for more.", "min_seconds": 2,
         "props": {"headline": "Follow Margin Notes", "button": "Follow"}},
    ]},
    "ar": {"aspect": "9x16", "theme": "brand", "scenes": [
        {"id": "hook", "type": "KineticTitle", "vo": "هذا اختبار سريع للمصنع.",
         "props": {"kicker": "اختبار", "title": "كل المشاهد تعمل", "highlight": ["تعمل"]}},
        {"id": "list", "type": "FeatureList", "vo": "الصوت والترجمة والموسيقى تعمل.",
         "props": {"title": "ماذا نختبر", "items": [{"text": "الصوت", "icon": "١"}, {"text": "الترجمة", "icon": "٢"}, {"text": "الموسيقى", "icon": "٣"}]}},
        {"id": "cta", "type": "CTAEndCard", "vo": "تابعوا مارجن نوتس للمزيد.", "min_seconds": 2,
         "props": {"headline": "تابعوا Margin Notes", "button": "متابعة"}},
    ]},
    "ru": {"aspect": "16x9", "theme": "light", "scenes": [
        {"id": "hook", "type": "KineticTitle", "vo": "Это быстрая проверка фабрики.",
         "props": {"kicker": "Тест", "title": "Все сцены работают", "highlight": ["работают"]}},
        {"id": "ba", "type": "BeforeAfter", "vo": "Было вручную, стало автоматически.",
         "props": {"before": {"label": "Было", "text": "Вручную"}, "after": {"label": "Стало", "text": "Автоматически"}}},
        {"id": "cta", "type": "CTAEndCard", "vo": "Подписывайтесь на Margin Notes.", "min_seconds": 2,
         "props": {"headline": "Подписывайтесь", "button": "Подписаться"}},
    ]},
}

AI_SCENE = {"id": "ai_shot", "type": "StoryShot", "vo": "",
            "props": {"text": "Local AI image", "letterbox": True},
            "visual": {"source": "ai_image", "prompt": "cinematic film still, a cup of tea on a wooden table by a snowy window, soft morning light", "seed": 7}}


def step(name: str, *args, env=None) -> None:
    cmd = [sys.executable, str(ROOT / "tools" / name), *map(str, args)]
    print(f"  $ {name} {' '.join(map(str, args[1:]))}", flush=True)
    r = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if r.returncode:
        print(r.stdout[-1500:], r.stderr[-1500:], sep="\n")
        raise RuntimeError(f"{name} exited {r.returncode}")


def run_case(lang: str, quick: bool, online: bool, with_ai: bool) -> list[str]:
    case = CASES[lang]
    run = RUNS / f"{date.today().isoformat()}_demo_smoke-test_{lang}"
    shutil.rmtree(run, ignore_errors=True)
    subprocess.run([sys.executable, str(ROOT / "tools/new_project.py"), "--brand", "demo",
                    "--title", "Smoke test", "--lang", lang], check=True, capture_output=True)
    scenes = [dict(s) for s in case["scenes"]]
    if with_ai:
        scenes.insert(1, dict(AI_SCENE))
    save_json(run_paths(run)["storyboard"], {
        "title": f"Smoke test {lang}", "brand": "demo", "language": lang, "goal": "educational",
        "aspects": [case["aspect"]], "theme": case["theme"], "music_mood": "calm",
        "captions": True, "image_provider": "local", "scenes": scenes})

    env = {**os.environ, "FACTORY_OFFLINE": "1"}
    step("validate_storyboard.py", run_paths(run)["storyboard"], env=env)
    step("make_voiceover.py", run, "--engine", "edge" if online else "piper", env=env)
    if with_ai:
        step("gen_image.py", run, env=env)
    step("pick_music.py", run, env=env)
    step("build_props.py", run, env=env)
    step("render.py", run, *(["--preview"] if quick else []), env=env)
    step("qa_frames.py", run, env=env)

    failed = []
    for qa in sorted(run_paths(run)["qa"].glob("qa_*.json")):
        report = load_json(qa)
        for c in report["checks"]:
            mark = "PASS" if c["ok"] else ("FAIL" if c["name"] in MUST_PASS else "warn")
            print(f"    {mark} {c['name']}: {c['detail']}")
            if mark == "FAIL":
                failed.append(f"{lang} {qa.stem}: {c['name']} ({c['detail']})")
        missing = MUST_PASS - {c["name"] for c in report["checks"]}
        failed += [f"{lang} {qa.stem}: check {m} did not run" for m in sorted(missing)]
    print(f"    contact sheet: {next(run_paths(run)['qa'].glob('contact_*.jpg'), 'none')}")
    return failed


POST_SPEC = {
    "brand": "demo", "topic": "Smoke test post", "goal": "educational", "language": "en", "aspect": "4x5",
    "platforms": ["linkedin", "instagram"], "posting_time": "Tue 09:00",
    "variants": [
        {"id": "A", "angle": "One number", "format": "single", "theme": "dark",
         "copy": {"linkedin": "Smoke test post A.", "instagram": "Smoke test A.", "hashtags": ["test"], "alt": "A card with a number."},
         "slides": [{"layout": "stat", "props": {"kicker": "Smoke test", "value": "3", "label": "layouts in **one** check"}}]},
        {"id": "B", "angle": "Step by step", "format": "carousel", "theme": "dark",
         "copy": {"linkedin": "Smoke test post B.", "instagram": "Smoke test B.", "alt": "Three slides: a list, a comparison and a call to action."},
         "slides": [{"layout": "list", "props": {"title": "What we check", "items": ["Layouts render", "Fonts load", "Delivery works"]}},
                    {"layout": "compare", "theme": "light", "props": {"title": "Before and after", "before": {"label": "Before", "items": ["By hand"]}, "after": {"label": "After", "items": ["Automatic"]}}},
                    {"layout": "cta", "props": {"headline": "Follow **Margin Notes**", "button": "Follow"}}]},
        {"id": "C", "angle": "A quote", "format": "single", "theme": "brand",
         "copy": {"linkedin": "Smoke test post C.", "instagram": "Smoke test C.", "alt": "A quote card."},
         "slides": [{"layout": "quote", "props": {"quote": "Every slide renders the same way twice.", "author": "Smoke test"}}]},
    ],
}


def run_post_case() -> list[str]:
    from PIL import Image
    run = ROOT / ".tmp/posts" / f"{date.today().isoformat()}_demo_smoke-test-post"
    out = ROOT / "output" / run.name
    shutil.rmtree(run, ignore_errors=True)
    run.mkdir(parents=True)
    save_json(run / "post.json", POST_SPEC)
    env = {**os.environ, "FACTORY_OFFLINE": "1"}
    step("validate_post.py", run / "post.json", env=env)
    step("render_post.py", run, "--no-images", env=env)
    step("deliver_post.py", run, "--pick", "B", env=env)
    failed = []
    index = load_json(run / "previews/index.json")
    for v in POST_SPEC["variants"]:
        slides = index.get(v["id"], {}).get("slides", [])
        if len(slides) != len(v["slides"]):
            failed.append(f"post {v['id']}: {len(slides)} preview(s), expected {len(v['slides'])}")
        for sp in slides:
            size = Image.open(ROOT / sp).size
            if size != (1080, 1350):
                failed.append(f"post {sp}: size {size}, expected (1080, 1350)")
    errors = [i for i in index.get("checks", {}).get("issues", []) if i["severity"] == "error"]
    failed += [f"post design check {i['variant']}{i['slide']}: {i['message']}" for i in errors]
    for f in ("slide_01.png", "slide_02.png", "slide_03.png", "cover.jpg", "carousel.pdf", "post.md", "post.json", "credits.txt"):
        if not (out / f).exists():
            failed.append(f"post delivery: missing {f}")
    if (out / "carousel.pdf").exists():
        pdf = (out / "carousel.pdf").read_bytes()
        pages = pdf.count(b"/Type /Page") - pdf.count(b"/Type /Pages")
        if pages < 3:
            failed.append(f"post delivery: carousel.pdf has {pages} page(s), expected 3")
    md = (out / "post.md").read_text(encoding="utf-8") if (out / "post.md").exists() else ""
    for h in ("## LinkedIn", "## Instagram", "## Alt text"):
        if h not in md:
            failed.append(f"post delivery: post.md lacks {h}")
    checks = index.get("checks", {})
    print(f"    previews: {sum(len(index.get(v['id'], {}).get('slides', [])) for v in POST_SPEC['variants'])} slide(s), "
          f"design check: {len(checks.get('issues', []))} issue(s) in {checks.get('seconds')}s")
    print(f"    contact sheet: {run / 'previews/contact.jpg'}")
    shutil.rmtree(out, ignore_errors=True)
    return failed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="Arabic 9x16 preview only")
    ap.add_argument("--langs", default="", help="comma list, default en,ar,ru (quick: ar)")
    ap.add_argument("--online", action="store_true", help="use edge-tts instead of the offline Piper voice")
    ap.add_argument("--with-ai", action="store_true", help="add a local sd.cpp StoryShot (slow)")
    ap.add_argument("--no-post", action="store_true", help="skip the HyperFrames post case")
    ap.add_argument("--post-only", action="store_true", help="run only the HyperFrames post case")
    args = ap.parse_args()

    langs = [] if args.post_only else args.langs.split(",") if args.langs else (["ar"] if args.quick else list(CASES))
    failed, t0 = [], time.time()
    for lang in langs:
        print(f"\n== smoke {lang} {CASES[lang]['aspect']}{' (preview)' if args.quick else ''}", flush=True)
        t = time.time()
        try:
            failed += run_case(lang, args.quick, args.online, args.with_ai)
        except Exception as e:
            failed.append(f"{lang}: {e}")
        print(f"  ({time.time() - t:.0f}s)")
    cases = len(langs)
    if not args.no_post:
        print("\n== smoke post 4x5 (HyperFrames: 3 variants, carousel delivery)", flush=True)
        t = time.time()
        try:
            failed += run_post_case()
        except Exception as e:
            failed.append(f"post: {e}")
        print(f"  ({time.time() - t:.0f}s)")
        cases += 1
    print(f"\n{'SMOKE FAIL' if failed else 'SMOKE PASS'} · {cases} case(s) in {time.time() - t0:.0f}s")
    for f in failed:
        print(f"  - {f}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
