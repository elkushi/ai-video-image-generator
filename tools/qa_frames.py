"""Automatic QA for a rendered video: contact sheet + measurable checks.

Contact sheet: one frame at 0.5 s (the hook) and one at the middle of every scene, labelled,
with the platform's unsafe zones tinted red (Reels/TikTok UI on 9:16). The video-qa-reviewer
agent looks at this image; the numbers go into qa.json.
Checks: duration vs props, resolution, audio stream, loudness (LUFS), long black stretches.
Audio checks (QA can't hear, so it transcribes): faster-whisper (local) transcribes the voice once per run
and compares it with each scene's VO -> vo_match (share of script words heard), vo_cut (the last line is
there), engine (edge vs the Piper fallback). Per-scene scores go to qa.json "asr".

Usage:
  python tools/qa_frames.py .tmp/videos/<run> [--video renders/Video-9x16.preview.mp4] [--no-asr]
Writes <run>/qa/contact_<name>.jpg and <run>/qa/qa_<name>.json; prints PASS/WARN lines.
"""
import argparse
import json
import re
import subprocess
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from common import config, duration, load_json, probe_size, run_paths, save_json, split_langs
from events import emit, rel

UNSAFE_9x16 = (220 / 1920, 380 / 1920)  # top, bottom fraction covered by app UI


def grab(video: Path, t: float, out: Path, width: int) -> Image.Image:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1",
                    "-vf", f"scale={width}:-2", str(out)], check=True)
    return Image.open(out).convert("RGB")


def loudness(video: Path) -> float | None:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(video), "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    return float(m[-1]) if m else None


def black_spans(video: Path) -> list[tuple[float, float]]:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(video), "-vf", "blackdetect=d=0.6:pix_th=0.06",
                        "-an", "-f", "null", "-"], capture_output=True, text=True)
    return [(float(a), float(b)) for a, b in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", r.stderr)]


def has_audio(video: Path) -> bool:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                        "-of", "csv=p=0", str(video)], capture_output=True, text=True)
    return bool(r.stdout.strip())


AR_FOLD = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه", "ـ": None, "ё": "е"})


def norm_words(text: str) -> list[str]:
    """Lowercase, drop punctuation and Arabic diacritics, fold alef/ya/ta-marbuta variants."""
    text = unicodedata.normalize("NFKC", text).lower().translate(AR_FOLD)
    # drop every combining mark: Arabic tashkeel and the Russian stress acute (U+0301) that some scripts carry
    text = unicodedata.normalize("NFD", text)
    text = "".join(" " if unicodedata.category(c)[0] in "PS" else c for c in text if unicodedata.category(c) != "Mn")
    text = unicodedata.normalize("NFC", text)
    return text.split()


def heard(word: str, pool: list[str]) -> bool:
    return any(w == word or SequenceMatcher(None, w, word).ratio() >= 0.75 for w in pool)


class Ear:
    """Local Whisper over the rendered audio: decoded once, transcribed whole (main language) or per window."""

    def __init__(self, video: Path, model: str):
        import numpy as np
        from faster_whisper import WhisperModel
        # decode with ffmpeg (faster-whisper's own PyAV decoder breaks on some PyAV versions)
        raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000",
                              "-f", "f32le", "-"], capture_output=True, check=True).stdout
        self.np, self.audio = np, np.frombuffer(raw, np.float32)
        self.model = WhisperModel(model, device="cpu", compute_type="int8")
        self.cache: dict = {}

    def whole(self, lang: str) -> list[tuple[float, float, str]]:
        if lang not in self.cache:
            segs, _ = self.model.transcribe(self.audio, language=lang, word_timestamps=True, beam_size=1, vad_filter=False)
            self.cache[lang] = [(w.start, w.end, w.word.strip()) for seg in segs for w in (seg.words or [])]
        return self.cache[lang]

    def window(self, a: float, b: float, lang: str) -> list[str]:
        x = self.audio[max(0, int(a * 16000)):int(b * 16000)]
        x = self.np.pad(x, (8000, 8000))  # Whisper is unreliable on very short clips without context
        segs, _ = self.model.transcribe(x, language=lang, beam_size=1, vad_filter=False)
        return [n for seg in segs for n in norm_words(seg.text)]


def match_count(script: list[str], pool: list[str]) -> int:
    hit = sum(heard(w, pool) for w in script)
    # numbers: scripts spell them out ("ninety-nine"), Whisper writes digits ("99"). Let each digit group
    # in what was heard account for up to 3 unmatched script words.
    digits = sum(1 for w in pool if any(ch.isdigit() for ch in w))
    return min(len(script), hit + min(len(script) - hit, digits * 3))


def asr_checks(ear: "Ear", props: dict, timeline: dict, cfg: dict) -> tuple[list, list]:
    fps = cfg["fps"]
    lang = props["language"]
    words = ear.whole(lang)
    tl_words = {t["id"]: t.get("words", []) for t in timeline.get("scenes", [])}
    scored, said, got = [], 0, 0
    for s in props["scenes"]:
        vo = s.get("vo") or ""
        runs = split_langs(vo, lang)
        tw = tl_words.get(s["id"], [])
        run_tokens = [[w for w in p.split() if any(ch.isalnum() for ch in w)] for _, p in runs]
        if len(runs) > 1 and sum(map(len, run_tokens)) == len(tw):
            # mixed-language line: hear each run in ITS language, which also checks the foreign word sounded native
            k, hit, n, parts = 0, 0, 0, []
            for (rl, rp), toks in zip(runs, run_tokens):
                seg = tw[k:k + len(toks)]
                k += len(toks)
                script = norm_words(rp)
                if not seg or not script:
                    continue
                pool = ear.window(seg[0][0] - 0.15, seg[-1][1] + 0.3, rl)
                h = match_count(script, pool)
                hit, n = hit + h, n + len(script)
                parts.append(f"[{rl}] " + " ".join(pool))
            if n:
                said, got = said + n, got + hit
                scored.append({"id": s["id"], "match": round(hit / n, 2), "heard": " · ".join(parts)[:200], "mixed": True})
            continue
        # single-language line (or timings that don't line up): main-language words against the whole transcript
        script = norm_words(" ".join(p for l, p in runs if l == lang))
        if not script:
            continue
        a, b = s["from"] / fps - 0.3, (s["from"] + s["duration"]) / fps + 0.3
        pool = [n for t0, t1, w in words if a <= (t0 + t1) / 2 <= b for n in norm_words(w)]
        hit = match_count(script, pool)
        said, got = said + len(script), got + hit
        scored.append({"id": s["id"], "match": round(hit / len(script), 2), "heard": " ".join(pool)[:160]})
    qcfg = cfg.get("qa", {})
    need = qcfg.get("vo_match_min", {}).get(lang, 0.6)
    total = got / said if said else 1.0
    worst = min(scored, key=lambda x: x["match"]) if scored else None
    engine = timeline.get("engine", "")
    engines = set(engine if isinstance(engine, list) else [engine])
    checks = [
        ("vo_match", total >= need, f"{total:.0%} of script words heard (min {need:.0%})"
         + (f"; weakest {worst['id']} {worst['match']:.0%}" if worst else "")),
        ("vo_cut", not scored or scored[-1]["match"] >= 0.3, f"last spoken scene {scored[-1]['id']} {scored[-1]['match']:.0%}" if scored else "no VO"),
        ("engine", engines <= {"edge"}, f"voice engine {sorted(engines)}" + ("" if engines <= {"edge"} else " (Piper fallback voice" + ("; Arabic becomes MSA" if lang == "ar" else "")
                  + ". Re-run --from voice when online)")),
    ]
    return checks, scored


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run", type=Path)
    ap.add_argument("--video", default="")
    ap.add_argument("--no-asr", action="store_true", help="skip the transcription checks")
    args = ap.parse_args()

    cfg = config()
    p = run_paths(args.run)
    props = load_json(p["props"])
    fps = cfg["fps"]
    videos = [args.run / args.video] if args.video else sorted(p["renders"].glob("*.mp4"))
    p["qa"].mkdir(exist_ok=True)
    timeline = load_json(p["timeline"]) if p["timeline"].exists() else {}
    has_vo = any((s.get("vo") or "").strip() for s in props["scenes"])
    asr_words = None  # the voice track is the same in every aspect, so transcribe once
    for video in videos:
        name = video.stem
        tmp = p["qa"] / "frames"
        tmp.mkdir(exist_ok=True)
        w, h = probe_size(video)
        dur = duration(video)
        thumb_w = 360 if h > w else 480
        shots = [(0.5, "hook 0.5s")] + [((s["from"] + s["duration"] / 2) / fps, f"{s['id']} · {s['type']}") for s in props["scenes"]]
        shots.append(((props["totalFrames"] - 5) / fps, "last frame"))
        imgs = []
        for i, (t, label) in enumerate(shots):
            im = grab(video, min(t, dur - 0.05), tmp / f"{name}_{i:02d}.jpg", thumb_w)
            d = ImageDraw.Draw(im, "RGBA")
            if h / w > 1.5:
                top, bot = UNSAFE_9x16
                d.rectangle([0, 0, im.width, int(im.height * top)], fill=(255, 0, 0, 50))
                d.rectangle([0, int(im.height * (1 - bot)), im.width, im.height], fill=(255, 0, 0, 50))
            d.rectangle([0, im.height - 30, im.width, im.height], fill=(0, 0, 0, 170))
            d.text((8, im.height - 24), f"{t:.1f}s {label}"[:48], fill=(255, 255, 255, 255),
                   font=ImageFont.load_default(size=16))
            imgs.append(im)
        cols = 6 if h > w else 4
        rows = (len(imgs) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * imgs[0].width + (cols + 1) * 8, rows * imgs[0].height + (rows + 1) * 8), (30, 30, 30))
        for i, im in enumerate(imgs):
            sheet.paste(im, (8 + (i % cols) * (im.width + 8), 8 + (i // cols) * (im.height + 8)))
        sheet_path = p["qa"] / f"contact_{name}.jpg"
        sheet.save(sheet_path, quality=88)

        checks = []
        expected = props["totalFrames"] / fps
        checks.append(("duration", abs(dur - expected) < 0.4, f"{dur:.2f}s (expected {expected:.2f}s)"))
        checks.append(("audio", has_audio(video), "audio stream present"))
        lufs = loudness(video)
        target = cfg["loudness_lufs"]
        checks.append(("loudness", lufs is not None and abs(lufs - target) <= 3,
                       f"{lufs} LUFS (target {target}; postprocess.py normalises)"))
        blacks = black_spans(video)
        checks.append(("black_frames", not blacks, f"black spans: {blacks}" if blacks else "none"))
        checks.append(("hook_length", props["scenes"][0]["duration"] / fps <= 4.5,
                       f"first scene {props['scenes'][0]['duration'] / fps:.1f}s (keep the hook under ~4s)"))
        asr = []
        if has_vo and not args.no_asr:
            try:
                if asr_words is None:
                    asr_words = Ear(video, cfg.get("qa", {}).get("asr_model", "base"))
                    save_json(p["qa"] / "transcript.json", asr_words.whole(props["language"]))
                more, asr = asr_checks(asr_words, props, timeline, cfg)
                checks += more
            except Exception as e:  # ASR is a check, never a blocker
                print(f"  ! ASR skipped: {e}")
        fallbacks = [f"{s['id']}: {s['visual'].get('fallback_used')}" for s in props["scenes"] if s["visual"].get("fallback_used")]
        report = {"video": str(video), "size": [w, h], "duration": dur, "lufs": lufs, "contact_sheet": str(sheet_path),
                  "fallbacks": fallbacks, "asr": asr, "checks": [{"name": n, "ok": ok, "detail": d} for n, ok, d in checks]}
        (p["qa"] / f"qa_{name}.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
        emit(args.run, "asset", "qa", type="contact_sheet", video=name, path=rel(sheet_path, args.run))
        emit(args.run, "check", "qa", video=name, fallbacks=fallbacks,
             checks=[{"name": n, "ok": ok, "detail": d} for n, ok, d in checks])
        print(f"== {name} ({w}x{h}, {dur:.1f}s)  sheet: {sheet_path}")
        for n, ok, d in checks:
            print(f"  {'PASS' if ok else 'WARN'} {n}: {d}")
        for f in fallbacks:
            print(f"  NOTE fallback {f}")


if __name__ == "__main__":
    main()
