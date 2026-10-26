"""Synthesize the voiceover scene by scene and record word timings (free).

Engine 1: edge-tts (Microsoft neural voices, free, online) with WordBoundary timings.
Engine 2 (fallback/offline, whole video only - never mixed): Piper voices (downloaded once to .tmp/models/piper), word
timings estimated proportionally to word length.
Each scene is synthesized separately so scene cuts land exactly on sentence boundaries;
silent scenes (no "vo") get min_seconds (or config silent_scene_seconds) of silence.
Mixed-language lines (an English sentence that quotes a Russian or Arabic word) are split into language
runs (common.split_langs) and each run is voiced by a native voice of the same gender, a touch slower, then
stitched with a short pause - so a word in another language never gets the wrong accent. Storyboard
"mixed_voices": "auto" (default) | "marked" (only [[en:...]] markup) | "off"; "voices": {"en": "..."} overrides.

Usage:
  python tools/make_voiceover.py .tmp/videos/<run> [--engine edge|piper] [--voice NAME] [--rate +5%]
Writes <run>/public/voice.wav and <run>/timeline.json; prints the total duration.
"""
import argparse
import asyncio
import shutil
import sys
import time
import urllib.request
import wave
from pathlib import Path

from common import ROOT, brand, config, duration, ff, load_json, plain_vo, run_paths, save_json, split_langs
from events import emit

PIPER_DIR = ROOT / ".tmp/models/piper"
PIPER_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/{lang}/{loc}/{name}/{q}/{file}"


async def edge_tts(text: str, voice: str, rate: str, mp3: Path) -> list[list]:
    import edge_tts as et
    words = []
    c = et.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    with mp3.open("wb") as f:
        async for ch in c.stream():
            if ch["type"] == "audio":
                f.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                s = ch["offset"] / 1e7
                words.append([round(s, 3), round(s + ch["duration"] / 1e7, 3), ch["text"]])
    return words


def piper_model(name: str) -> Path:
    loc, speaker, q = name.split("-")
    onnx = PIPER_DIR / f"{name}.onnx"
    if not onnx.exists():
        PIPER_DIR.mkdir(parents=True, exist_ok=True)
        for file in (f"{name}.onnx", f"{name}.onnx.json"):
            url = PIPER_URL.format(lang=loc.split("_")[0], loc=loc, name=speaker, q=q, file=file)
            print(f"  downloading piper voice {file} ...", flush=True)
            urllib.request.urlretrieve(url, PIPER_DIR / file)
    return onnx


def piper_tts(text: str, model: str, out_wav: Path) -> list[list]:
    from piper import PiperVoice
    voice = PiperVoice.load(str(piper_model(model)))
    with wave.open(str(out_wav), "wb") as wf:
        voice.synthesize_wav(text, wf)
    total = duration(out_wav)
    # proportional word timings across the clip (good enough for captions on a fallback path)
    toks = text.split()
    weights = [len(t) + 2 for t in toks]
    span, t, words = total * 0.96, total * 0.02, []
    for tok, w in zip(toks, weights):
        d = span * w / sum(weights)
        words.append([round(t, 3), round(t + d, 3), tok])
        t += d
    return words


class EdgeFailed(Exception):
    pass


def edge_variants(text: str) -> list[str]:
    """edge-tts deterministically returns NO audio for some lines with some voices ("Это слово — привет." with
    Dmitry, while Svetlana reads it) and tiny inaudible edits fix it. Try them before giving up."""
    out = [text]
    add = lambda v: v not in out and out.append(v)
    if text[:1].isupper():
        add(text[0].lower() + text[1:])           # lower-case first letter: sounds identical
    add(text.replace(" — ", ", ").replace(" - ", ", "))
    add(text.rstrip(".") + "…" if text.endswith(".") else text + ".")
    add(text + " ")
    add(text.rstrip(".") + "!" if text.endswith(".") else text)
    return out


def synth(text: str, out_base: Path, engine: str, voice: str, rate: str, piper_name: str) -> tuple[Path, list]:
    """One scene with ONE engine. edge-tts is retried with backoff; persistent failure raises EdgeFailed
    so the caller re-voices the whole video with Piper (never mix two voices in one video)."""
    if engine == "edge":
        # edge-tts garbles U+0301 stress marks ("приве́т" -> "привете", some marked lines return no audio) and
        # stresses standard words correctly on its own: speak the bare text, keep the marks on screen.
        text = text.replace("\u0301", "")
        mp3 = out_base.with_suffix(".mp3")
        for attempt, variant in enumerate(edge_variants(text)):
            for net_try in range(2):
                try:
                    words = asyncio.run(edge_tts(variant, voice, rate, mp3))
                    if mp3.exists() and mp3.stat().st_size > 0:
                        if variant != text:
                            print(f"  (edge-tts accepted variant {attempt}: {variant[:50]!r})", flush=True)
                        return mp3, words
                except Exception as e:  # network hiccup, 503, rate limit, or the NoAudioReceived quirk
                    print(f"  ! edge-tts {voice} try {attempt}.{net_try}: {str(e)[:100]}", file=sys.stderr)
                    if "No audio" in str(e):
                        break  # deterministic for this text: try the next variant now
                time.sleep(2 * (net_try + 1))
        raise EdgeFailed(text[:40])
    wav = out_base.with_suffix(".raw.wav")
    return wav, piper_tts(text, piper_name, wav)


def is_female(voice: str, cfg: dict) -> bool:
    return any(f in voice for f in cfg.get("female_voices", [])) or voice.endswith(("irina-medium",))


def shift_rate(rate: str, delta: int) -> str:
    try:
        v = int(str(rate).strip().rstrip("%")) + delta
    except ValueError:
        v = delta
    return f"{v:+d}%"


class Mixer:
    """Picks the voice for each language run of a line, and stitches the runs into one clip."""

    def __init__(self, sb: dict, kit: dict, cfg: dict, main_voice: str, main_piper: str):
        self.sb, self.kit, self.cfg, self.lang = sb, kit, cfg, sb["language"]
        self.main_voice, self.main_piper = main_voice, main_piper
        mcfg = cfg.get("mixed_voice", {})
        self.mode = sb.get("mixed_voices", "auto")
        self.delta = int(mcfg.get("foreign_rate_delta", -8))
        self.gap = float(mcfg.get("gap_seconds", 0.14))
        self.keep = set(mcfg.get("keep_words", [])) | set(kit.get("name", "").split()) | set(kit.get("mixed_voice_keep", []))
        self.female = is_female(main_voice, cfg)
        self.used: dict[str, str] = {}
        self.sub: dict[str, str] = {}  # a foreign voice that kept failing -> its same-language substitute

    def runs(self, text: str) -> list[tuple[str, str]]:
        if self.mode == "off":
            return [(self.lang, plain_vo(text))]
        return split_langs(text, self.lang, self.keep, auto=self.mode == "auto")

    def voice_for(self, lang: str, engine: str) -> str:
        if lang == self.lang:
            return self.main_voice if engine == "edge" else self.main_piper
        spec = self.cfg["languages"].get(lang, {})
        if engine == "piper":
            return (spec.get("piper_female") if self.female else None) or spec.get("piper")
        over = (self.sb.get("voices") or {}).get(lang)
        if over:
            return over
        cands = [self.kit.get("voices", {}).get(lang)] + spec.get("voices", [])
        return next((v for v in cands if v and is_female(v, self.cfg) == self.female), cands[1] if len(cands) > 1 else cands[0])

    def synth_line(self, text: str, base: Path, engine: str, rate: str) -> tuple[Path, list]:
        runs = self.runs(text)
        if len(runs) == 1 and runs[0][0] == self.lang:
            return synth(runs[0][1], base, engine, self.main_voice if engine == "edge" else self.main_piper, rate, self.main_piper)
        parts, words, t = [], [], 0.0
        for k, (lang, piece) in enumerate(runs):
            v = self.sub.get(lang) or self.voice_for(lang, engine)
            r = rate if lang == self.lang else shift_rate(rate, self.delta)
            pbase = base.with_name(f"{base.name}_p{k}")
            try:
                src, w = synth(piece, pbase, engine, v, r, v if engine == "piper" else self.main_piper)
            except EdgeFailed:
                if lang == self.lang:
                    raise  # the main voice must stay one voice: caller re-voices the whole video with Piper
                # a short foreign word can be refused by one voice (Dmitry: "привет.") - use another native voice
                alts = [x for x in self.cfg["languages"][lang].get("voices", []) if x != v]
                for alt in alts:
                    try:
                        src, w = synth(piece, pbase, engine, alt, r, self.main_piper)
                        print(f"  ({lang} run: {v} refused it, using {alt} for this language)", flush=True)
                        v = self.sub[lang] = alt
                        break
                    except EdgeFailed:
                        continue
                else:
                    raise
            self.used[lang] = v
            d = duration(src)
            # trim the TTS padding between runs (keep the natural start of the first and end of the last)
            a = max(0.0, w[0][0] - 0.04) if (k > 0 and w and engine == "edge") else 0.0
            b = min(d, w[-1][1] + 0.12) if (k < len(runs) - 1 and w and engine == "edge") else d
            seg = base.with_name(f"{base.name}_p{k}.seg.wav")
            ff("-i", src, "-af", f"atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS", "-ar", "48000", "-ac", "2", seg)
            parts.append(seg)
            words += [[round(s0 - a + t, 3), round(s1 - a + t, 3), tok] for s0, s1, tok in w]
            t += (b - a)
            if k < len(runs) - 1:
                gap = base.with_name(f"{base.name}_g{k}.wav")
                ff("-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", f"{self.gap:.3f}", gap)
                parts.append(gap)
                t += self.gap
        out = base.with_suffix(".mixed.wav")
        lst = base.with_name(f"{base.name}_parts.txt")
        lst.write_text("".join(f"file '{x.resolve()}'\n" for x in parts))
        ff("-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out)
        return out, words


def voice_all(sb: dict, work: Path, engine: str, voice: str, rate: str, piper_name: str, cfg: dict, mixer: "Mixer"):
    t, wavs, scenes = 0.0, [], []
    for i, s in enumerate(sb["scenes"]):
        text = s.get("vo", "").strip()
        base = work / f"{i:02d}_{s['id']}"
        words, speech = [], 0.0
        wav = base.with_suffix(".wav")
        emit(work.parent, "progress", "voice", scene=s["id"], i=i, n=len(sb["scenes"]), engine=engine,
             text=text[:120])
        if text:
            src, words = mixer.synth_line(text, base, engine, rate)
            speech = duration(src)
            dur = max(speech + cfg["scene_pause"], s.get("min_seconds", 0))
            ff("-i", src, "-af", f"apad=whole_dur={dur:.3f}", "-ar", "48000", "-ac", "2", wav)
        else:
            dur = s.get("min_seconds") or cfg["silent_scene_seconds"]
            ff("-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", f"{dur:.3f}", wav)
        wavs.append(wav)
        scenes.append({"id": s["id"], "start": round(t, 3), "dur": round(dur, 3), "speech": round(speech, 3),
                       "words": [[round(t + a, 3), round(t + b, 3), w] for a, b, w in words]})
        t += dur
    return t, wavs, scenes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run", type=Path)
    ap.add_argument("--engine", choices=["edge", "piper"], default="edge")
    ap.add_argument("--voice", default="")
    ap.add_argument("--rate", default="")
    args = ap.parse_args()

    cfg = config()
    p = run_paths(args.run)
    sb = load_json(p["storyboard"])
    lang = sb["language"]
    kit = brand(sb["brand"])
    voice = args.voice or sb.get("voice") or kit.get("voices", {}).get(lang) or cfg["languages"][lang]["voices"][0]
    rate = args.rate or sb.get("voice_rate") or kit.get("voice_rate") or cfg["voice_rate"]
    # offline fallback voice: explicit, else the same gender as the edge voice (ru has a female Piper voice)
    female = any(f in voice for f in cfg.get("female_voices", []))
    piper_name = (sb.get("piper_voice") or (cfg["languages"][lang].get("piper_female") if female else None)
                  or cfg["languages"][lang]["piper"])

    work = args.run / "voice_parts"
    shutil.rmtree(work, ignore_errors=True)  # stale parts from an earlier engine must not leak in
    work.mkdir()
    engine = args.engine
    mixer = Mixer(sb, kit, cfg, voice, piper_name)
    try:
        t, wavs, scenes = voice_all(sb, work, engine, voice, rate, piper_name, cfg, mixer)
    except EdgeFailed as e:
        print(f"  ! edge-tts unavailable (scene '{e}'); re-voicing the WHOLE video with Piper", file=sys.stderr)
        if lang == "ar":
            print("  ! Piper Arabic is formal MSA (Jordanian voice), not Egyptian; re-run later for edge-tts", file=sys.stderr)
        engine, voice = "piper", piper_name
        shutil.rmtree(work)
        work.mkdir()
        mixer.used = {}
        t, wavs, scenes = voice_all(sb, work, engine, voice, rate, piper_name, cfg, mixer)

    listfile = work / "list.txt"
    listfile.write_text("".join(f"file '{w.resolve()}'\n" for w in wavs))
    ff("-f", "concat", "-safe", "0", "-i", listfile, "-c", "copy", p["public"] / "voice.wav")
    save_json(p["timeline"], {"total": round(t, 3), "voice": voice, "rate": rate, "engine": engine,
                              "language": lang, "mixed_voices": mixer.used, "scenes": scenes})
    print(f"voice: {t:.1f}s via {engine} ({voice})" + (f"; other-language runs: {mixer.used}" if mixer.used else ""))


if __name__ == "__main__":
    main()
