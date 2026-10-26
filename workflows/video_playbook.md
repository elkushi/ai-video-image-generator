# Video playbook (reference for strategist, scriptwriter and QA)

This is a living reference, not a step-by-step SOP. Add what works, with the date, and remove what doesn't.

## Platform specs
| Platform | Aspect | Length that performs | Notes |
|---|---|---|---|
| Instagram Reels | 9x16 | 7–30 s (≤90 s) | Hook in 1 s. Top ~220 px and bottom ~380 px are covered by UI. Captions always on (most watch muted). |
| Instagram feed | 4x5 (or 1x1) | 15–45 s | 4x5 takes the most feed space. The cover frame matters. |
| LinkedIn feed | 1x1 or 4x5 | 15–45 s | Autoplays muted, so captions are essential. B2B tone; numbers and how-it-works beat hype. |
| LinkedIn mobile / vertical | 9x16 | 15–40 s | LinkedIn now has a vertical video feed. Reuse the Reels cut. |
| LinkedIn events / announcements | 1x1 + 9x16 | 20–35 s | Date, time and timezone on screen ≥ 3 s. Registration CTA on screen ≥ 2 s. |
| TikTok / YouTube Shorts | 9x16 | 15–45 s | The same cut works; the safe zones are similar. |
| YouTube / website / LinkedIn desktop | 16x9 | 45–120 s | Educational explainers and tutorials. |

Default for a B2B brand: **1x1 + 9x16**. Default for a consumer product: **9x16 + 4x5**.

## Formats (pick one per video)
| Format | Structure (scene types) | Use for |
|---|---|---|
| problem-solution-proof | KineticTitle hook (pain) → StockBroll/StoryShot (cost of pain) → ScreenDemo/ProductHero (solution) → FeatureList (how) → StatCounter (proof) → CTAEndCard | SaaS/app promos |
| product-showcase | ProductHero (fullBleed hook) → ProductHero ×2–3 (angles/features, each with one benefit) → Quote (review, only if real) → CTAEndCard | physical products |
| 3-tips / mistakes | KineticTitle ("3 mistakes…") → BeforeAfter/FeatureList ×3 → StatCounter or Quote → LogoReveal/CTA | educational, saves and shares |
| myth-vs-fact | KineticTitle ("Myth:") → BeforeAfter (myth → fact) ×2 → StatCounter → CTA | educational, contrarian |
| tutorial-walkthrough | KineticTitle (outcome) → ScreenDemo ×3–5 (focus + clicks per step) → CTAEndCard | SaaS onboarding, feature launch |
| event-announcement | KineticTitle (why attend) → StatCounter/Quote (credibility) → EventCard → CTAEndCard ("Register") | webinars, launches, meetups |
| feature-launch | KineticTitle ("New: …") → ScreenDemo → FeatureList (3 benefits) → CTAEndCard | announcements |
| story / short film | StoryShot ×4–8 (one character, one seed) → Presenter (lesson) → CTAEndCard/LogoReveal | brand storytelling, going viral |
| presenter talk | Presenter (hook) → KineticTitle/FeatureList cutaways → Presenter → CTA | founder POV, explainers |

## Hook formulas (first 1.5 s; VO ≤ 14 words, screen ≤ 7 words)
1. **Specific pain + number:** "Your OTP arrived. 40 seconds late."
2. **Contrarian:** "Cheaper SMS is costing you more."
3. **Callout:** "If you run a fintech app, watch this."
4. **Result first:** "We cut delivery time from 40 s to 2 s."
5. **Question you can't ignore:** "Why do 1 in 5 users never get their code?"
6. **Mistake list:** "3 mistakes that kill your sign-up rate."
7. **Story cold open:** "11 p.m. Amira lands in Dubai. Her bank asks for a code."
8. **Visual pattern-break:** an unexpected object or motion with a one-word title.

Never open with a logo, "Hi everyone", or a slow fade-in. The logo comes at the end (the watermark covers recognition).

## Retention rules
- A new visual every 2–4 s: scene change, zoom, list item or counter. One idea per scene.
- The on-screen text is the punchline, not the sentence. Captions carry the sentence.
- Put the payoff (number, result) by about 60% of the video. The CTA comes last, is shown ≥ 2 s and is spoken.
- For loops (Reels), the last line can lead back into the first.
- Educational videos: give a "save this" reason (a list or checklist). Events: urgency from real limits only (seats, date).

## Pacing per language (config/factory.json)
| Lang | Typical words/s | Max words/s | Notes |
|---|---|---|---|
| en | 2.3 | 2.9 | Andrew (calm male), Ava (warm female), Ryan (British male) |
| ar | 1.9 | 2.3 | MSA by default. Shakir/Salma (Egyptian), Hamed/Zariyah (Saudi). Write brand names phonetically in VO. Keep Latin names on screen. Arabic-Indic digits come from the locale automatically. |
| ru | 2.0 | 2.4 | Dmitry/Svetlana. Use «вы» for B2B. Lines run ~15% longer than English, so cut words. |

## Scene library (studio/src/scenes)
| Type | Props | Best visual source |
|---|---|---|
| KineticTitle | title, subtitle?, kicker?, highlight?[], align? | none, or a stock/AI background (dimmed) |
| LogoReveal | tagline? | brand logo (automatic) |
| ProductHero | title?, caption?, kicker?, fullBleed? | file (product photo), ai_image, stock_photo |
| ScreenDemo | title?, kicker?, device phone/laptop, focus?[{at,x,y,scale}], clicks?[{at,x,y}] | screenshot (capture_screens.py) |
| FeatureList | title, kicker?, items[{text, icon?, sub?}] (icon: brand asset path or 1–2 chars) | none |
| StatCounter | value, label, prefix?, suffix?, decimals?, kicker?, source? | none |
| BeforeAfter | title?, before{label,text}, after{label,text} | none |
| Quote | quote, author?, role? | none (real quotes only) |
| EventCard | kicker?, title, date, time?, location?, speakers?[{name, role?, photo?}], button? | none, plus speaker photos in assets/people |
| StockBroll | text?, kicker?, position? | stock_video / stock_photo |
| StoryShot | text?, letterbox?, chapter? | ai_clip / ai_image (Ken Burns fallback) |
| Presenter | title?, text?, name?, role?, kicker? | avatar (AI talking head) / mascot |
| CTAEndCard | headline, button?, url?, sub? | brand logo (automatic) |

Transitions (`scene.transition`):
- simple: `fade`, `slide`, `zoom`, `wipe`, `none`
- cinematic: `light-leak` (warm, emotional), `zoom-blur` (energy), `clock-wipe` (time and steps), `glitch` / `rgb-split` (tech; they flash cyan, so check the brand's colour rules), `pixelate`, `checkerboard`

Use 1–2 kinds per video, never a different one on every cut. Storyboard `look: {grain: 0.05, vignette: 0.3}` adds film texture; it's on by default for `goal: story`. A scene's `lottie: {src: "assets/lottie/x.json", position: "top-right", size: 28}` adds an animated sticker: free Lottie JSONs go in `brands/<slug>/assets/lottie/`.

Themes: `dark` (default, brand dark background), `light`, `brand` (primary-colour background; Arabic event videos looked best this way).

## AI visual prompting (free FLUX / Pollinations)
- Prompt structure: subject + action + setting + light + lens + mood + "no text". The brand `image_style` is appended automatically.
- Character consistency: copy the same character sentence into every prompt and use the same `seed`.
- Avoid text in images, hands close-up, logos and real people's likeness.
- AI clips: describe motion ("slowly turns to camera", "camera dolly forward"). Expect at most 4 s and a few per day with an HF token.

## Local image prompting (sd.cpp + DreamShaper 8 LCM, SD1.5-based)
- Keep prompts short and concrete: "cinematic film still, <character sentence>, <action>, <place>, <light>". Long FLUX-style paragraphs get truncated (77 tokens).
- SD1.5 handles faces at mid-shot well and hands badly. Frame mid or wide, hide hands (pockets, holding a cup), and avoid text and signs.
- Consistency: same seed + same character sentence + the same brand `image_style`. For a recurring character, generate one good portrait, save it as `brands/<slug>/assets/characters/<name>.png`, and set `visual.ref` (img2img, `strength` 0.55–0.7) on the shots where he's central.
- Set `"image_provider": "local"` on story videos so the whole film uses one model.

## Sound design (automatic, `build_props.py`)
whoosh on each cut (softer for stories), impact on a promo/event hook, pop per FeatureList item, ticks while a StatCounter counts, click on ScreenDemo clicks, chime on the CTA end card. Use `scene.sfx: "none"` to mute a scene, or a tag to add one; set `"sfx": false` in the storyboard to turn it all off.

## Free asset sources
- Stock: Pexels and Pixabay APIs (`.env` keys). Credits are logged automatically.
- Music: download from Pixabay Music or the YouTube Audio Library into `assets/music/` and register each track in `music.json`.
- Fonts: Google Fonts (OFL) via `extract_brand.py --font`.

## Learnings log
- 2026-10-21: Arabic event announcement in the `brand` theme + 1x1 reads cleanly. Primary-filled chips needed a `pill` colour (secondary) to stay visible on a primary background.
- 2026-10-21: 16:9 needed a 1.2× type scale; text sized for 1080-wide portrait looked small on a 1920 canvas.
