"""Merge storyboard + voice timeline + resolved assets + brand kit into props.json for Remotion.

Also copies file/screenshot visuals from the brand folder into the run's public dir and turns
word timings into @remotion/captions Caption objects (script punctuation preserved).

Usage:
  python tools/build_props.py .tmp/videos/<run>
Writes <run>/props.json and prints scene count + duration.
"""
import argparse
import shutil
import wave
from pathlib import Path

import numpy as np

from common import BRANDS, ROOT, brand, config, load_json, run_paths, save_json, plain_vo

SFX_DIR = ROOT / "assets/sfx"


def resolve_files(sb: dict, public: Path) -> None:
    for s in sb["scenes"]:
        v = s.get("visual") or {"source": "none"}
        if v["source"] in ("file", "screenshot") and v.get("path") and not v.get("resolved"):
            src = Path(v["path"]) if Path(v["path"]).is_absolute() else BRANDS / sb["brand"] / v["path"]
            cut = src.with_name(f"{src.stem}_cutout.png")
            if s["type"] == "ProductHero" and cut.exists():  # tools/cutout.py output: product on transparent bg
                src = cut
                s.setdefault("props", {})["cutout"] = True
            dst = public / "visuals" / f"{s['id']}_{src.name}"
            dst.parent.mkdir(exist_ok=True)
            shutil.copy(src, dst)
            video = src.suffix.lower() in (".mp4", ".mov", ".webm", ".m4v")
            v.update(resolved=f"visuals/{dst.name}", kind="video" if video else "image")


def voice_levels(wav_path: Path, fps: int, frames: int) -> list[float]:
    """Per-frame loudness 0-1 of the voiceover (drives the mascot's mouth)."""
    with wave.open(str(wav_path)) as w:
        sr, ch = w.getframerate(), w.getnchannels()
        data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)
    mono = data.reshape(-1, ch).mean(axis=1) / 32768
    hop = sr / fps
    rms = np.array([np.sqrt(np.mean(mono[int(i * hop):int((i + 1) * hop)] ** 2) + 1e-12) for i in range(frames)])
    ref = np.percentile(rms[rms > 0.01], 90) if (rms > 0.01).any() else 1
    return [round(float(min(1.0, v / ref)), 2) for v in rms]


def plan_sfx(sb: dict, scenes: list, fps: int, public: Path) -> list[dict]:
    """Auto sound design: whoosh on cuts, impact on a promo hook, pops per list item, ticks on counters,
    clicks on ScreenDemo clicks, chime on the end card. scene "sfx": "<tag>" adds one, "none" mutes a scene."""
    if not sb.get("sfx", True):
        return []
    meta_p = SFX_DIR / "sfx.json"
    if not meta_p.exists():
        return []
    lib: dict[str, list[str]] = {}
    for m in load_json(meta_p):
        if (SFX_DIR / m["file"]).exists():
            lib.setdefault(m["tag"], []).append(m["file"])
    use = {t: 0 for t in lib}
    story = sb["goal"] == "story"
    events = []

    def add(tag: str, frame: int, vol: float):
        if tag not in lib:
            return
        f = lib[tag][use[tag] % len(lib[tag])]
        use[tag] += 1
        events.append({"frame": max(0, int(frame)), "src": f"sfx/{f}", "volume": vol})

    src_scenes = {s["id"]: s for s in sb["scenes"]}
    for i, sc in enumerate(scenes):
        own = src_scenes[sc["id"]].get("sfx")
        if own == "none":
            continue
        if own:
            add(own, sc["from"], 0.5)
        if i == 0 and not story and sb["goal"] in ("promo", "announcement", "event"):
            add("impact", 0, 0.35)
        if i > 0 and sc.get("transition", "fade") != "none":
            add("whoosh", sc["from"] - 6, 0.18 if story else 0.3)
        if sc["type"] == "FeatureList":
            n = len(sc["props"].get("items", []))
            window = max(20, (sc.get("speechFrames") or sc["duration"]) * 0.8)
            for k in range(n):
                add("pop", sc["from"] + 10 + (0 if n <= 1 else k * max(0, window - 10) / n), 0.35)
        if sc["type"] == "StatCounter":
            end = min(sc["duration"] * 0.6, 45)
            for f in range(4, int(end), 4):
                add("tick", sc["from"] + f, 0.12)
        if sc["type"] == "ScreenDemo":
            for c in sc["props"].get("clicks", []):
                add("click", sc["from"] + c.get("at", 0) * sc["duration"], 0.4)
        if sc["type"] == "CTAEndCard":
            add("chime", sc["from"] + 14, 0.3)
    if events:
        out = public / "sfx"
        out.mkdir(exist_ok=True)
        for e in events:
            shutil.copy(SFX_DIR / Path(e["src"]).name, out / Path(e["src"]).name)
    return sorted(events, key=lambda e: e["frame"])


def captions_for(scene_words: list, vo: str) -> list[dict]:
    # punctuation-only tokens ("—") have no word boundary; drop them so the script maps 1:1 to the timings
    script = [w for w in vo.split() if any(ch.isalnum() for ch in w)]
    use_script = len(script) == len(scene_words)
    caps = []
    for i, (a, b, w) in enumerate(scene_words):
        text = script[i] if use_script else w
        caps.append({"text": f" {text}", "startMs": round(a * 1000), "endMs": round(b * 1000),
                     "timestampMs": round((a + b) * 500), "confidence": None})
    return caps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run", type=Path)
    args = ap.parse_args()

    cfg = config()
    fps = cfg["fps"]
    p = run_paths(args.run)
    sb = load_json(p["storyboard"])
    tl = load_json(p["timeline"])
    kit = brand(sb["brand"])
    resolve_files(sb, p["public"])
    # runs created before fonts went local: make sure the fallback fonts are in the public dir
    if not (p["public"] / "fonts").exists():
        shutil.copytree(ROOT / "assets/fonts", p["public"] / "fonts")
    save_json(p["storyboard"], sb)

    timing = {t["id"]: t for t in tl["scenes"]}
    total_frames = round(tl["total"] * fps)
    scenes, captions, ranges = [], [], []
    for i, s in enumerate(sb["scenes"]):
        t = timing[s["id"]]
        start = round(t["start"] * fps)
        nxt = round(tl["scenes"][i + 1]["start"] * fps) if i + 1 < len(sb["scenes"]) else total_frames
        v = s.get("visual") or {"source": "none"}
        scenes.append({
            "id": s["id"], "type": s["type"], "vo": plain_vo(s.get("vo", "")), "from": start, "duration": max(1, nxt - start),
            "speechFrames": round(t["speech"] * fps), "transition": s.get("transition", "fade"),
            "props": s.get("props", {}),
            "visual": {k: v.get(k) for k in ("source", "resolved", "kind", "motion", "fallback_used") if k in v},
            **({"lottie": {**s["lottie"], "src": "brand/" + s["lottie"]["src"].lstrip("/")}} if s.get("lottie") else {}),
        })
        if t["words"]:
            captions += captions_for(t["words"], plain_vo(s.get("vo", "")))
            ranges.append([round(t["words"][0][0] * fps), round(t["words"][-1][1] * fps)])

    music_meta = args.run / "music.json"
    music = load_json(music_meta) if music_meta.exists() else {"src": None}
    m = cfg["music"]
    props = {
        "title": sb["title"],
        "language": sb["language"],
        "dir": cfg["languages"][sb["language"]]["dir"],
        "theme": sb.get("theme") or kit.get("theme_default", "dark"),
        "brand": {k: kit[k] for k in ("name", "tagline", "website", "handle", "colors", "fonts", "logo", "radius", "motif") if k in kit},
        "brandBase": "brand/",
        "scenes": scenes,
        "totalFrames": total_frames,
        "transitionFrames": cfg["transition_frames"],
        "look": sb.get("look") or ({"grain": 0.05, "vignette": 0.35} if sb.get("goal") == "story" else None),
        "voice": "voice.wav" if (p["public"] / "voice.wav").exists() else None,
        "music": {"src": music["src"], "underVoice": m["under_voice"], "noVoice": m["no_voice"],
                  "fadeFrames": round(m["fade_seconds"] * fps)} if music.get("src") else None,
        "voiceRanges": ranges,
        "sfx": plan_sfx(sb, scenes, fps, p["public"]),
        "voiceLevels": voice_levels(p["public"] / "voice.wav", fps, total_frames) if (p["public"] / "voice.wav").exists() else [],
        "captions": captions,
        "showCaptions": sb.get("captions", True),
        "captionStyle": sb.get("caption_style", "highlight"),
        "progressBar": sb.get("progress_bar", True),
        "watermarkLogo": sb.get("watermark_logo", True),
    }
    save_json(p["props"], props)
    print(f"props: {len(scenes)} scenes, {total_frames} frames ({tl['total']:.1f}s), {len(captions)} caption words, "
          f"{len(props['sfx'])} sfx")


if __name__ == "__main__":
    main()
