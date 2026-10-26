---
name: onboard-brand
description: Create a brand kit (brands/<slug>/) for the video factory from a logo, website, guidelines or product info. Use when the user says "/onboard-brand" or introduces a new client, product or app.
argument-hint: <name> [website] [attached logo/guidelines]
---

# /onboard-brand

Arguments: `$ARGUMENTS`.

1. Read `workflows/onboard_brand.md` and follow it.
2. Draft the kit with `tools/extract_brand.py`. Then review `brand.json` by hand (contrast, logos, voices, rules) and write `profile.md` from facts the user or the website states only.
3. Run the smoke test the workflow describes (a 10 s title + CTA in each brand language). Check the contact sheet for fonts, colours and Arabic/Cyrillic glyphs.
4. Report what is ready and what's missing (e.g. a white logo, product photos).

Client kits are gitignored and stay local: they may hold licensed fonts and internal facts.
