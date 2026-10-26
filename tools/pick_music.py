"""Choose background music for a run (free, always succeeds).

Order:
  1. Local library assets/music/ described by assets/music/music.json (royalty-free tracks you
     downloaded once from Pixabay Music / YouTube Audio Library). Best mood match, least used.
  2. Free MusicGen Space on Hugging Face (config music_gen.hf_spaces), if --allow-ai.
  3. Built-in synth bed generated locally with numpy: pad chords, bass, plucked arpeggio, a bell motif and
     a lift at ~58% of the video (the payoff point), plus a kick/hat pulse for upbeat moods.
storyboard music_mood "none" -> no music.

Usage:
  python tools/pick_music.py .tmp/videos/<run> [--mood upbeat] [--allow-ai]
Writes <run>/public/music.<ext> and <run>/music.json {src, source, credit}.
"""
import argparse
import json
import shutil
import sys
import wave
from pathlib import Path

import numpy as np

from common import ROOT, add_credit, brand, config, load_json, run_paths, save_json

LIB = ROOT / "assets/music"
SR = 44100

# mood -> (bpm, chord roots in semitones from A3, minor?, pulse?)
MOODS = {
    "upbeat":    (112, [0, 7, 9, 5], False, True),
    "tech":      (104, [9, 5, 0, 7], True, True),
    "playful":   (118, [0, 5, 7, 5], False, True),
    "corporate": (96,  [0, 9, 5, 7], False, True),
    "inspiring": (84,  [5, 0, 7, 9], False, False),
    "calm":      (72,  [0, 5, 9, 7], False, False),
    "dramatic":  (70,  [9, 5, 0, 7], True, False),
}


def note(freq: float, secs: float, kind: str = "pad") -> np.ndarray:
    t = np.linspace(0, secs, int(SR * secs), endpoint=False)
    if kind == "pad":
        wave_ = sum(np.sin(2 * np.pi * freq * m * t + d) / (i + 1) ** 1.6
                    for i, (m, d) in enumerate([(1, 0), (2.003, 0.3), (3.001, 1.1), (0.5, 0.0)]))
        env = np.minimum(1, t / 0.9) * np.minimum(1, (secs - t) / 1.2)
    else:  # pluck
        wave_ = np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(2 * np.pi * freq * 2 * t)
        env = np.exp(-t * 7)
    return wave_ * np.clip(env, 0, 1)


def synth_bed(mood: str, seconds: float, out: Path) -> Path:
    bpm, roots, minor, pulse = MOODS.get(mood, MOODS["corporate"])
    beat = 60 / bpm
    bar = beat * 4
    total = int(SR * (seconds + 2))
    mix = np.zeros(total)
    third = 3 if minor else 4
    t0, i = 0.0, 0
    while t0 < seconds + 2:
        r = roots[i % len(roots)]
        base = 220 * 2 ** (r / 12)
        chord = [base / 2, base, base * 2 ** (third / 12), base * 2 ** (7 / 12)]
        seg = sum(note(f, bar * 2) for f in chord) * 0.16
        s = int(t0 * SR)
        mix[s:s + len(seg)] += seg[: total - s]
        for k in range(8):  # arpeggio, one pluck per beat
            f = chord[1:][k % 3] * (2 if k % 4 == 3 else 1)
            p = note(f * 2, beat * 0.9, "pluck") * 0.07
            ps = int((t0 + k * beat) * SR)
            if ps < total:
                mix[ps:ps + len(p)] += p[: total - ps]
        t0 += bar * 2
        i += 1
    # bass: chord root, one octave down, on beats 1 and 3
    t0, i = 0.0, 0
    while t0 < seconds + 2:
        base = 220 * 2 ** (roots[i % len(roots)] / 12) / 4
        for k in (0, 2, 4, 6):
            b = note(base, beat * 1.6, "pluck") * 0.22
            bs = int((t0 + k * beat) * SR)
            if bs < total:
                mix[bs:bs + len(b)] += b[: total - bs]
        t0 += bar * 2
        i += 1
    # bell lead: a simple 4-note motif from the chord, enters at the "lift" (~60% = payoff in the playbook)
    lift = seconds * 0.58
    rng = np.random.default_rng(len(roots) + bpm)
    t0 = lift
    while t0 < seconds - 1.5:
        r = roots[int(t0 / (bar * 2)) % len(roots)]
        base = 440 * 2 ** (r / 12)
        scale = [0, 4 if not minor else 3, 7, 12]
        for k in range(4):
            f = base * 2 ** (scale[int(rng.integers(0, 4))] / 12)
            tt = np.linspace(0, beat * 1.8, int(SR * beat * 1.8), endpoint=False)
            bell = (np.sin(2 * np.pi * f * tt) + 0.25 * np.sin(2 * np.pi * f * 2.76 * tt)) * np.exp(-tt * 2.8) * 0.06
            bs = int((t0 + k * beat) * SR)
            if bs < total:
                mix[bs:bs + len(bell)] += bell[: total - bs]
        t0 += bar
    # lift: +25% energy after the payoff point
    gain = np.ones(total)
    ls = int(lift * SR)
    gain[ls:] = np.minimum(1.25, 1 + np.arange(total - ls) / (SR * 2) * 0.25)
    mix *= gain
    if pulse:
        n = int(seconds / beat) + 2
        tk = np.linspace(0, 0.25, int(SR * 0.25), endpoint=False)
        kick = np.sin(2 * np.pi * (48 + 60 * np.exp(-tk * 30)) * tk) * np.exp(-tk * 14) * 0.35
        hat = np.random.default_rng(1).normal(0, 1, int(SR * 0.04)) * np.exp(-np.linspace(0, 6, int(SR * 0.04))) * 0.03
        for k in range(n):
            s = int(k * beat * SR)
            if s + len(kick) < total:
                mix[s:s + len(kick)] += kick
            h = int((k + 0.5) * beat * SR)
            if h + len(hat) < total:
                mix[h:h + len(hat)] += hat
    kernel = np.ones(6) / 6  # gentle low-pass
    mix = np.convolve(mix, kernel, mode="same")
    mix = mix[: int(SR * seconds)]
    mix *= np.minimum(1, np.arange(len(mix)) / (SR * 1.5)) * np.minimum(1, (len(mix) - np.arange(len(mix))) / (SR * 2))
    mix = mix / (np.abs(mix).max() + 1e-9) * 0.8
    stereo = np.stack([mix, np.roll(mix, 220)], axis=1)
    with wave.open(str(out), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes((stereo * 32767).astype(np.int16).tobytes())
    return out


def from_library(mood: str, seconds: float) -> dict | None:
    meta = LIB / "music.json"
    if not meta.exists():
        return None
    tracks = [t for t in json.loads(meta.read_text()) if (LIB / t["file"]).exists()]
    if not tracks:
        return None
    usage_p = LIB / "usage.json"
    usage = json.loads(usage_p.read_text()) if usage_p.exists() else {}
    def score(t):
        return (mood in t.get("moods", []), t.get("seconds", 999) >= seconds * 0.6, -usage.get(t["file"], 0))
    best = max(tracks, key=score)
    if mood not in best.get("moods", []):
        return None
    usage[best["file"]] = usage.get(best["file"], 0) + 1
    usage_p.write_text(json.dumps(usage, indent=2))
    return best


def music_gen(mood: str, seconds: float, out: Path) -> str:
    import hf_space
    prompt = {"upbeat": "upbeat modern pop instrumental, bright synths, claps",
              "tech": "minimal electronic tech background, pulsing synths",
              "corporate": "light corporate background music, piano and soft beat",
              "inspiring": "inspiring cinematic piano and strings, uplifting",
              "calm": "calm ambient pads, soft piano, relaxing",
              "dramatic": "dramatic cinematic trailer underscore, low strings",
              "playful": "playful ukulele and whistles, light percussion"}.get(mood, "soft background music")
    for space in config()["music_gen"]["hf_spaces"]:
        try:
            res = hf_space.call(space, "/predict", model="facebook/musicgen-small", text=prompt, melody=None,
                                duration=min(30, int(seconds) + 2), topk=250, topp=0, temperature=1, cfg_coef=3)
            hf_space.keep(res, out)
            return space
        except Exception as e:
            print(f"  ! {str(e)[:200]}", file=sys.stderr)
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run", type=Path)
    ap.add_argument("--mood", default="")
    ap.add_argument("--allow-ai", action="store_true", help="try the MusicGen Space before the synth bed")
    args = ap.parse_args()

    p = run_paths(args.run)
    sb = load_json(p["storyboard"])
    kit = brand(sb["brand"])
    mood = args.mood or sb.get("music_mood") or (kit.get("music_moods") or ["corporate"])[0]
    out_meta = args.run / "music.json"
    if mood == "none":
        save_json(out_meta, {"src": None})
        print("music: none")
        return
    seconds = load_json(p["timeline"])["total"] if p["timeline"].exists() else 60

    track = from_library(mood, seconds)
    if track:
        src = LIB / track["file"]
        dst = p["public"] / f"music{src.suffix}"
        shutil.copy(src, dst)
        credit = f"\"{track.get('title', src.stem)}\" - {track.get('license', 'royalty-free')} ({track.get('source', '')})"
        add_credit(args.run, {"type": "music", "credit": credit, "source": track.get("source", "")})
        save_json(out_meta, {"src": dst.name, "source": "library", "credit": credit})
        print(f"music: library '{src.name}' ({mood})")
        return
    if args.allow_ai:
        dst = p["public"] / "music_ai.wav"
        used = music_gen(mood, seconds, dst)
        if used:
            add_credit(args.run, {"type": "music", "credit": f"AI-generated music ({used})", "source": used})
            save_json(out_meta, {"src": dst.name, "source": used, "credit": "AI-generated"})
            print(f"music: {used} ({mood})")
            return
    dst = synth_bed(mood, seconds, p["public"] / "music_synth.wav")
    save_json(out_meta, {"src": dst.name, "source": "synth", "credit": "Original synth bed (generated locally)"})
    print(f"music: built-in synth bed ({mood}); add tracks to assets/music/ for better results")


if __name__ == "__main__":
    main()
