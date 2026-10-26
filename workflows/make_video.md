# Workflow: Make a video (brief → finished files)

## Objective
Turn "brand + topic" into finished, on-brand short videos for LinkedIn and Instagram (and TikTok/Shorts/web) with **zero spend**. Claude acts as strategist, scriptwriter, motion designer and QA. Deterministic tools do the rendering. The user approves only the final video.

## Inputs
| Input | Required | Where it comes from |
|---|---|---|
| Brand slug | yes | `brands/<slug>/`. If it's missing, run `workflows/onboard_brand.md` first |
| Topic / what the video is about | yes | the user |
| Goal | infer | promo, educational, event, story, announcement or tutorial |
| Platforms | infer | default LinkedIn feed (1x1) + Reels (9x16); events: 1x1 + 9x16 |
| Language(s) | infer | en / ar / ru. Default is the brand's main market. One run per language |
| Event details | for events | title, date, time and timezone, place or online, speakers, registration link |
| Must-say points, CTA, link | optional | otherwise from `profile.md` |

Ask the user **only** for blocking gaps, in one message: event date/time/link, an unknown product fact, or a missing language choice. Infer everything else.

Brief the user can paste (every line optional except brand + topic):
```
Brand: <slug or "new: name + attach logo/site/guidelines">
Topic: <what the video is about>
Goal: promo | educational | event | story | announcement | tutorial
Where: LinkedIn | Instagram | TikTok | YouTube | website
Language: en | ar | ru (several = one video each)
Length: ~<seconds>
Must say: <facts, offer, feature>
CTA / link: <...>
Event: <title, date, time + timezone, online/place, speakers, registration link>
Style: motion graphics | product shots | screen demo | stock | AI story | presenter
```

## Tools (all in `tools/`, run with `.venv/bin/python`)
| Step | Tool | Free provider / fallback |
|---|---|---|
| Run folder | `new_project.py` | — |
| Validate | `validate_storyboard.py` | — |
| Voice | `make_voiceover.py` | edge-tts (online, retried 4×), else Piper (offline) for the **whole** video; voices are never mixed |
| Stock | `fetch_stock.py` | Pexels, then Pixabay (free keys, not set up: user chose no accounts), falling back to a motion card |
| AI image | `gen_image.py` | HF FLUX (anonymous quota), then **local sd.cpp** (`local_image.py`, unlimited), then Pollinations. One provider per video (sticky, or `image_provider`) |
| Upscale | `upscale.py` | Real-ESRGAN ncnn-vulkan on the MX350, falling back to Lanczos (called by `local_image.py`) |
| Look | storyboard `look` {grain, vignette}, scene `lottie`, cinematic transitions | film grain, vignette and 7 transitions from claude-code-video-toolkit (MIT) in `studio/src/lib/transitions`; Lottie via @remotion/lottie |
| AI clip | `animate_image.py` | HF Wan/LTX, then **local depth parallax** (`depth_parallax.py`), then Ken Burns on the still |
| Avatar | `make_avatar.py` | HF MoDA/EchoMimic, falling back to the built-in mascot |
| Product cut-out | `cutout.py` | rembg isnet (local); ProductHero uses `*_cutout.png` automatically |
| Music | `pick_music.py` | local library, then (opt-in) MusicGen, then the synth bed v2 (pads, bass, bell motif, lift at about 58%) |
| SFX | `make_sfx.py` (once) + `build_props.py` | generated library in `assets/sfx/`, placed automatically (whoosh, pop, tick, click, impact, chime) |
| Local models | `setup_local_models.py [--bench]` | downloads and checks everything in `.tmp/models/` |
| Props | `build_props.py` | — |
| Render | `render.py` | Remotion on CPU |
| QA | `qa_frames.py` | contact sheet + checks, plus audio checks via local Whisper transcription (`vo_match`, `vo_cut`, `engine`) |
| Regression | `smoke_test.py [--quick]` | renders tiny EN/AR/RU videos offline and asserts QA passes |
| Deliver | `postprocess.py` | −14 LUFS, output folder |
| Orchestrate | `run_video.py` | runs validate → … → preview, or `--final` |

## Steps

1. **Intake.** Read `brands/<slug>/profile.md` and `brand.json`, then list `brands/<slug>/assets/`. Create the run (one per language):
   `python tools/new_project.py --brand <slug> --title "<working title>" --brief "<topic, goal, CTA, details>" [--lang ar]`
2. **Strategy.** Spawn the `video-strategist` agent with the run path and brand slug, and save its answer as `<run>/strategy.md`. If it lists blocking questions, ask the user, then continue.
   - SaaS/app with no screenshots yet: run `python tools/capture_screens.py --brand <slug> --url <app or site url>` (add `--full` for long scroll shots).
3. **Storyboard.** Spawn the `video-scriptwriter` agent. It writes `<run>/storyboard.json` and must get a PASS from `validate_storyboard.py`. For several languages, write the main language first, then one storyboard per extra language in its own run folder, written natively rather than translated.
4. **Produce + preview.** Run `python tools/run_video.py <run>`. This runs validate, voice, assets, props, a half-scale preview render and QA, and takes about 2–4 min for a 30 s video.
5. **QA loop (max 2 rounds).** Spawn `video-qa-reviewer` with the run path.
   - `FIX`: apply the blocking fixes. Text and timing changes go in storyboard.json, then rerun from `voice` if VO changed, otherwise from `props`. Layout bugs go to `remotion-motion-designer`. Then run `run_video.py <run> --from props` again.
   - `SHIP`: continue.
6. **Final.** Run `python tools/run_video.py <run> --from props --final`, which renders every aspect at full quality and then runs QA, loudness normalisation and delivery to `output/<run-name>/`.
7. **Post copy.** Write `output/<run-name>/post.md` yourself (the `social-content` skill helps). It contains:
   - a LinkedIn post (hook line, 3–5 short lines, CTA, 3–5 hashtags)
   - an Instagram caption (hook, value, CTA, up to 8 hashtags)
   - alt text for the cover
   - the suggested posting time for the audience's timezone
   - the AI-disclosure note from `credits.txt`

   The text is in the video's language.
8. **Present.** Show the user the output folder, each MP4 path, `post.md`, and any fallbacks used (e.g. "stock fell back to motion cards: add a Pexels key"). The user approves or asks for changes. Changes go back to step 3 or 5.
9. **Learn.** Add new quirks to "Known quirks" below, and new format insights to `video_playbook.md`.

## Series and learning
- Several videos for one brand: plan them with `workflows/content_calendar.md` (agent `content-planner`). Each approved calendar item is the brief for one run of this workflow.
- After posting: `workflows/review_performance.md` records the stats in `brands/<slug>/performance.md`, which the strategist reads first.

## Changing the factory itself
After editing any tool, scene, config or dependency, run `python tools/smoke_test.py --quick` (~2 min, offline). Before a big batch, or after Remotion/npm/pip upgrades, run the full `python tools/smoke_test.py`. Fix any `SMOKE FAIL` before making client videos. The checks are numbers, so also look at the printed contact sheet: the RTL word-order bug below passed every check.

## Multi-language runs
- Keep one run folder per language (`--lang ar`) so files never collide.
- Arabic: theme `brand` or `dark` reads best. All caption styles animate whole words, so Arabic letters stay joined. The hook text must be Arabic even if the brand name is Latin.
- Russian: lines run ~15% longer than English, so cut words rather than shrinking the font.

## Short films / story videos
- Use goal `story` and 5–10 `StoryShot` scenes, all `ai_clip` or `ai_image` with one character description and one seed.
- The free GPU quota covers only a few AI clips a day. Run `animate_image.py` early, and accept Ken Burns on the rest. Add `HF_TOKEN` to `.env` for more quota.
- Use music mood `dramatic`/`inspiring`, `letterbox: true`, and end on a `CTAEndCard` or `LogoReveal`.

## Known quirks (learned 2026-10-21)
- **Local-only mode** (the user's choice: no accounts). `FACTORY_OFFLINE=1` skips every remote AI provider. Without it, the free anonymous providers are still tried first.
- **Pollinations now answers `402 Payment Required`** after 2–3 anonymous images. `gen_image.py` disables it for the rest of the run.
- **Local images (sd.cpp + DreamShaper 8 LCM)** look good (cinematic, consistent palette) but are slow on this laptop: about 9 min per image on CPU and 11 min on the MX350 via Vulkan, measured at 384×672 with only ~1.8 GB of RAM free. CPU is the default (`config local.sd_backend`). Budget for it: generate stills first (`gen_image.py <run>`), then the rest. Close the browser/IDE to free RAM; swap thrashing makes it 2–3× slower.
- **Real-ESRGAN:** use Vulkan device 1 (NVIDIA). Device 0 is the Intel iGPU and is 3× slower. `realesr-animevideov3` ×2 ≈ 8 s; `realesrgan-x4plus` ≈ 215 s, so don't use it.
- **Depth parallax** takes ~2 min per 4 s 1080×1920 clip on CPU, and looks best on shots with a clear foreground subject.
- **Egyptian Arabic pace:** `ar-EG-ShakirNeural` reads ~1.3 words/s at +0% and each "…" adds ~0.6 s, which the validator now models. Use `voice_rate` +8–12% and few ellipses for Reels.
- **HF ZeroGPU anonymous quota** is tiny: about 2 FLUX images used it all up, after which Wan/LTX/MoDA/EchoMimic answered "exceeded your ZeroGPU quota". A free `HF_TOKEN` raises it. Fallbacks (Pollinations, Ken Burns, mascot) worked automatically.
- **Pollinations** without a key returns about 580 px wide images from the "sana" model with a watermark strip at the bottom. `gen_image.py` crops it off. Use it only as a fallback.
- **edge-tts** takes about 5–8 s per scene over the network (a 6-scene VO took ~50 s). Word timings drop punctuation; `build_props.py` maps the script's own words back when the counts match.
- **First render** downloads Chrome Headless Shell (~99 MB) once. Bundling takes ~16 s per render call. A 26 s 9:16 preview at half scale rendered in ~50 s on this laptop (concurrency 2).
- The Reels/TikTok UI covers ~220 px at the top and ~380 px at the bottom of 1920. The layout keeps content in 330–1280 px with captions centred at ~1400 px, and the watermark sits at 240 px.
- **Faster-whisper's own decoder** (PyAV) crashes with `unexpected keyword argument 'metadata_errors'` on the installed PyAV. `qa_frames.py` decodes with ffmpeg and passes a numpy array instead. Whisper base scores ~94% on EN, ~86% on AR (MSA/Egyptian edge voices), ~77% on RU. The per-language minimums are in `config qa.vo_match_min`.
- **Mixed-language lines** (an English sentence that quotes a Russian or Arabic word). One voice reading a foreign word gives it the wrong accent: Whisper heard a Russian voice's "Hello, how are you?" as "Фило, хау-райу". English and Arabic voices return NO audio for Cyrillic at all, which used to push the whole video to Piper. `make_voiceover.py` now splits each line into language runs (`common.split_langs`: by script, or `[[en:…]]` markup), voices each run with a native same-gender voice at −8%, and stitches them with a 0.14 s pause. Brand names, `mixed_voice.keep_words` and short ALL-CAPS acronyms stay in the main voice. QA transcribes each run in its own language.
  - The edge Multilingual voices (Andrew/Ava/Brian/Emma Multilingual) return no audio for Russian text through the free endpoint, so they aren't an option.
- **edge-tts and stress marks:** edge *garbles* U+0301 ("приве́т" → "привете"/"приветая", and some marked lines return no audio). `synth()` strips the marks for edge only. Its Russian voices stress standard words correctly; homographs need a disambiguating context sentence. Piper keeps the marks. The marks always stay on screen.
- **edge-tts "No audio" quirk:** some voice + text pairs fail deterministically (Dmitry: "Это слово — привет.", "привет."). `edge_variants()` retries with inaudible edits (lower-case first letter, dash → comma, …). A foreign run then falls back to the other native voice of that language before the main voice ever falls back to Piper.
- **Russian stress marks and Inter:** neither the Google static Inter nor the official Inter 4.1 positions U+0301 on Cyrillic letters. Chrome draws "двери´", and the mark eats the next space. Montserrat and DejaVu are fine. `studio/src/lib/stress.tsx` (`st()`) now draws the accent as an overlay in every text component, so any brand font works. Keep the marks in the storyboard text.
- **Whisper small** (`config qa.asr_model`) replaced base: RU went from 77% to 96% and AR from 86% to 98% on clean edge voices, at ~30–50 s per QA run. Spelled-out numbers vs Whisper's digits are handled by a digit allowance in `asr_checks`.
- **RTL word order:** in word-animated Arabic text, each word is its own inline-block, so a Latin phrase came out reversed ("تابعوا Margin Notes" → "Lab Story تابعوا"). `bidiRuns()` in `studio/src/lib/anim.ts` now keeps consecutive Latin words in one LTR run, in both titles and captions.
- Full-page phone screenshots can be 40,000 px tall. Prefer viewport shots for `ScreenDemo`, and use `--full` only for scroll demos.

## Change log
- 2026-10-21: v1. Pipeline, 13 scenes, EN/AR/RU, free fallbacks for every AI step.
- 2026-10-21: v1.3 motion pack (glitch, light-leak, rgb-split, zoom-blur, clock-wipe, pixelate, checkerboard; grain/vignette; Lottie stickers), Russian stress-mark rendering + female Piper voice (irina), Whisper small for QA.
- 2026-10-21: v1.2 audio QA (Whisper), smoke_test.py, content calendar + performance loop, /video /onboard-brand /content-calendar commands, RTL Latin-run fix.
- 2026-10-21: v1.1 local stack. sd.cpp images, Real-ESRGAN, depth parallax, rembg, SFX, synth v2, single-engine VO, Arabic pace calibration, StoryShot motion-card fallback.
