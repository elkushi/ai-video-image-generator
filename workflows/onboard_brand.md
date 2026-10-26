# Workflow: Onboard a new brand

## Objective
Create `brands/<slug>/` once per client or product so every later video only needs a topic. The kit holds facts (`profile.md`), look (`brand.json`, logo, fonts) and real assets (product photos, screenshots, people).

## Inputs (whatever the user sends; nothing is mandatory except a name)
- **Physical product:** product photos (transparent PNG is ideal), logo, website/shop link, specs, price (if public), audience, what makes it different.
- **SaaS / app:** logo, brand guidelines (PDF/HTML/Figma export), app or site URL (plus a test login if screens are behind auth), feature list, pricing page, audience.
- **Events:** recurring event series, speaker photos with consent.
- **Any brand:** tone of voice, words to avoid, competitors not to name, approved numbers, CTA, social handles, main language(s).

## Steps
1. Pick a short slug (`acme`, `demo`).
2. Draft the kit:
   `python tools/extract_brand.py --slug <slug> --name "<Name>" [--logo <file>] [--logo-dark <file>] [--url <site>] [--font "<Google Font>"] [--primary "#hex"]`
   - It copies `brands/_template/`, extracts palette candidates from the logo and the live site CSS, downloads the Google Font (OFL, free), screenshots the homepage and saves the site text to `.tmp/site_<slug>.txt`.
   - If the guidelines name a licensed font the user owns, copy the files into `fonts/` and list them in `brand.json` → `fonts.*.files`. Check the licence covers video. If it doesn't, use the closest Google Font.
3. **Review `brand.json` by hand.** The extractor guesses; fix it against the guidelines.
   - `primary` is the main brand colour. `dark` must read well under white text (contrast ≥ 4.5:1).
   - `logo.on_light` and `logo.on_dark`: a reversed (white) logo for dark themes matters, so ask for one if it's missing.
   - Set `voices` per language: test with `edge-tts --list-voices | grep ar-`, and choose gender/accent to fit the audience.
   - Set `image_style` (used in every AI prompt), `music_moods`, `rules.do` / `rules.dont`.
4. **Write `profile.md`** from the template using the user's info and `.tmp/site_<slug>.txt`. Only include facts the user or the website states; mark anything uncertain as "unconfirmed" and keep it out of videos.
5. **Assets:** put product photos in `assets/products/`, screenshots in `assets/screens/` (`python tools/capture_screens.py --brand <slug> --url <url> [--full] [--scroll-video]`), and people in `assets/people/`. Name files descriptively (`dashboard_overview.png`, not `IMG_2041.png`).
6. **Smoke test:** make a 10 s `KineticTitle` + `CTAEndCard` run in each brand language with `run_video.py`, then look at the contact sheet for colours, logo, fonts and Arabic/Cyrillic glyphs.
7. Tell the user the kit is ready, and list anything still missing (e.g. a white logo or product photos).

## Edge cases
- **Logo only as JPG with a background:** the free `images_remove_background` paths are paid, so ask for a PNG/SVG. Otherwise use it on a light card (`theme: light`).
- **Brand colour too light for white text:** set `dark` to a deep neutral and use `primary` for accents only.
- **Website blocks headless browsers:** take screenshots manually, or ask the user for them.
- **No brand guidelines:** pick one Google Font and a palette from the logo, and confirm with the user in the final message.
