# Workflow: Make a social post (single image or carousel)

## Objective
Turn a brief ("LinkedIn post with a visual about X for <brand>") into **3 complete post packages** (copy plus visual). Each package uses a different angle and a different look. The user picks one, and the picked one is delivered as ready-to-upload files. This works for any brand in `brands/`. Nothing here is brand-specific: facts come from `profile.md` and the look from `brand.json`.

HyperFrames (`hyperframes/`, pinned CLI plus `templates/post.css`) renders posts. Remotion (`studio/`) renders videos.

## Inputs
- **Brand slug.** If `brands/<slug>/` doesn't exist, run `workflows/onboard_brand.md` first.
- **Topic / brief.** Optional: goal (educational, promo, event, brand), platforms (default LinkedIn and Instagram), language (default: the brand's main language), format (`single`, `carousel` or auto), aspect (default 4x5), must-say lines, CTA, event details, uploads, and whether an animated version is wanted.
- Ask once, and only for blocking gaps (an event date/time/link, or a fact not in the profile). In headless app runs, end with `@@QUESTION {...}` instead (`app/server/prompts/headless.md`).

## Steps
1. **Run folder:** `.venv/bin/python tools/new_post.py --brand <slug> --topic "<topic>" --brief "<brief lines and intake answers>"`. It prints `.tmp/posts/<date>_<brand>_<slug>-post`.
2. **Copy:** run the `post-copywriter` agent with the run folder, brand, platforms, language, goal and answers. It returns 3 distinct angles as JSON (copy per platform, alt text, the on-image message, a format hint, the posting time). If it reports `missing_facts` that block the post, ask (step 0 rule).
3. **Design:** run the `post-designer` agent with the run folder and the angles JSON. It writes `post.json` (`schemas/post.schema.json`), mixing themes and layouts across the variants, with at most one AI-photo variant.
4. **Validate:** `.venv/bin/python tools/validate_post.py .tmp/posts/<run>/post.json` must PASS (the designer does this; re-check if you edited the file).
5. **Render previews:** `.venv/bin/python tools/render_post.py .tmp/posts/<run>`. Add `--motion` only if an animated version was asked for, and `--variant B` to re-render one variant. Outputs: `previews/<V>/slide_NN.png`, `previews/contact.jpg`, `previews/index.json`.
6. **QA:** run `video-qa-reviewer` on the run (its "Posts / stills" section). Apply the blocking fixes through `post-designer` (edit `post.json`, validate, re-render). At most 2 rounds.
7. **Stop and present the 3 variants.** In the app (headless), the job ends here: don't run `deliver_post.py`. The final structured output must be `{"run": ".tmp/posts/<run>", "summary": "<one or two plain lines>", "variants": [{"id": "A", "angle": "...", "why": "..."}, ...]}` (`app/server/schemas/post_result.json`); the user picks in the UI and the app runs step 8. In chat, show the contact sheet path and a one-line summary per variant (angle, format, look), and ask which one to deliver and whether to change any copy.
8. **Deliver the pick:** `.venv/bin/python tools/deliver_post.py .tmp/posts/<run> --pick <A|B|C> [--copy-edits edits.json]`. `edits.json` is `{"linkedin": "...", "alt": "..."}`, any copy fields the user changed.

## Revise (feedback on existing variants)
- Edit only the variants named in the feedback (all of them if none are named) in the existing `.tmp/posts/<run>/post.json`. Keep the ids, and keep the other variants untouched.
- Copy changes go through `post-copywriter` when they change the angle; small wording or visual changes go straight to `post-designer`.
- Then validate, `render_post.py <run> --variant <V>` for each changed variant (or all), QA, and stop again at step 7 (in the app: the same structured result, with the same `run`).
- A picked post can be revised too; delivery overwrites `output/<run-name>/` when the user picks again.

## Commands
Every command runs from the repo root as `.venv/bin/python tools/<x>.py ...`, one per Bash call, without `cd`, pipes or `&&` (the app's headless allow-list rejects them).

## Output
`output/<run-name>/`:
- `slide_01.png` … (1080 px wide PNGs, one per slide) and `cover.jpg` (slide 1)
- `carousel.pdf` for carousels: upload it to LinkedIn as a document post; on Instagram, upload the PNGs in order
- `motion.mp4` (only if rendered with `--motion`)
- `post.md` (copy per platform with hashtags, alt text, posting time, how to post, an AI disclosure if a photo is AI)
- `post.json` (the picked variant plus the alternatives' angles), `brief.md`, `credits.txt`

## Edge cases and timing
- **FLUX quota gone or offline:** a `photo` slide with a prompt degrades to a title card with the same words, and `render_post.py` prints "falls back". `FACTORY_OFFLINE=1` uses local Stable Diffusion (about 9 min per image on this laptop), so prefer kit assets or a non-photo layout instead.
- **Long copy:** put it in the post copy, not on the image. If the idea has 3+ points, make it a carousel.
- **Missing fact** (date, price, link, number not in the profile): never invent it. Ask, or `@@QUESTION` when headless.
- **Arabic:** the builder sets RTL, the Cairo font and the mirrored swipe arrow; write the props in Arabic.
- **Thin brand kits** (no logo, icons, screens or handle): the builder falls back to a text wordmark, numbered or letter badges and an empty footer. Prefer `title`, `stat`, `list`, `compare` and `quote` over `icons`/`screen`, and tell the user which assets would improve the posts (a logo on light and dark, icons, screenshots).
- **Numbers not in profile.md** produce a validator WARN: confirm them or remove them.
- **Timing:** about 40 s per render pass for ~6 slides (Chrome start is most of it), plus 10-60 s per FLUX photo; `--motion` adds about 1-3 min per variant.
- **Low RAM** (HyperFrames doctor warns at about 1 GB free): render one variant at a time with `--variant`.
