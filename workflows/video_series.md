# Workflow: Video series from your topics (questions → bible → scripts → production)

## Objective
The user gives a list of topics, e.g. "three explainer videos: 1) X, 2) Y, 3) Z". Claude:
1. asks the questions that matter, **once for the whole series**;
2. writes a short series bible so every episode feels like one show;
3. writes every script;
4. produces every video, ready to post.

This differs from `content_calendar.md`, where Claude invents the topics. Here the user owns the topics and Claude owns everything else.

## Inputs
| Input | Required | Notes |
|---|---|---|
| Brand slug | yes | onboard first if it's missing (`onboard_brand.md`) |
| Topics | yes | 1–10, in order. Each can be one line or a paragraph of notes |
| Anything else | no | language, platform, length, style. Ask for what's missing (step 1) |

## Steps

### 1. Ask first (one round, before any writing)
Read `brands/<slug>/profile.md`, `brand.json`, `workflows/video_playbook.md` and `brands/<slug>/performance.md` (if it exists). Then ask **one** AskUserQuestion round (≤ 4 questions per call, two calls at most). Each question has concrete options with the recommended one first. Skip anything the brief, profile or playbook already answers. Pick from this list:

| Topic | Typical options |
|---|---|
| **What "educational in <language>" means** (only if it's ambiguous) | videos *in* a language about the brand's field, vs videos that *teach* that language |
| **Audience and level** | beginners / intermediate / experts; for language lessons, the learner level and the viewers' native language |
| **Series format** | the same structure every episode, e.g. 3-tips, myth-vs-fact, mini-lesson (word → example → practice), tutorial |
| **Length and platforms** | Reels/TikTok 9x16 ~30 s; LinkedIn 1x1 ~45 s; YouTube 16x9 ~90 s |
| **Tone and voice** | calm teacher, energetic, friendly peer; voice gender; formal vs informal address |
| **Visual style** | motion graphics (fastest, the default for education), screen demo, AI story, presenter/mascot |
| **On-screen help** (language lessons) | subtitles in the viewers' language, transliteration, stress marks |
| **Series identity** | a series name and episode numbering ("Ep. 2/3"), a recurring intro line, the same CTA each time |
| **Script review** | "Review the scripts before production" vs "Just make them (Recommended for speed)" |

Never invent facts. If a topic needs numbers or claims that aren't in `profile.md`, ask in this same round, or keep the script fact-free.

### 2. Series bible
Write `brands/<slug>/series/<series-slug>/bible.md`. It holds:
- name and promise (one line)
- audience and level
- language and voice (+ `voice_rate`)
- format template: the scene-type sequence and target seconds
- hook pattern
- recurring elements: intro line, episode tag, CTA, theme, music mood, caption style
- glossary: terms to keep consistent, transliteration rules, pronunciations (written phonetically for the VO)
- do/don't

Write `series.json` next to it:
- `{"brand", "series", "language", "aspects", "bible": "bible.md", "episodes": [...]}`
- each episode: `{"n", "topic", "notes", "status": "todo", "run": null}`

### 3. Write all the scripts first
For each episode, in order:
1. Create its run with `new_project.py --brand <slug> --title "<series> Ep<n>: <topic>" --lang <lang>`. The brief contains the topic, the user's notes and the path to `bible.md`.
2. Spawn `video-strategist` (it must follow the bible's format and hook pattern and only sharpen the angle), and save its answer as `strategy.md`.
3. Spawn `video-scriptwriter` with the bible. It writes `storyboard.json` and must PASS `validate_storyboard.py`.
4. **Language lessons only:** check the level, the new words and any stress marks yourself, fix what is wrong, then re-validate.

Writing every script before rendering catches repetition across episodes early. Compare the hooks and examples side by side, and rewrite any two that are too similar.

**If the user chose script review:** show one compact table with the episode number, hook (spoken and on-screen), the key points and the CTA. Then wait for "go" or edits; apply edits to the storyboards and re-validate. Otherwise continue straight on.

### 4. Produce
Go through the episodes in order, one at a time (RAM). For each, run `workflows/make_video.md` from step 4: preview → `video-qa-reviewer` (max 2 rounds) → final → `post.md`. Set its `status` to `"made"` and fill in `run`.
- Tag each `post.md` with the episode ("Ep. 2/3") and link the series in the caption ("Part 1 is on my profile").
- When fallbacks happen (e.g. no AI images), keep them consistent across the series. Don't mix looks between episodes.

### 5. Report
List each episode's output folder and MP4s, the suggested posting order and days (e.g. Tue/Thu/Sat), and any fallbacks used. Tell the user they can say "add episode 4: <topic>" to extend the series with the same bible.

## Edge cases
- **Very different topics:** keep the format template, but let each episode pick its own example visuals.
- **A topic is too big for one video:** propose splitting it into two episodes in the step 1 questions.
- **Language lessons:**
  - The VO speaks the target language slowly (`voice_rate` −5% to −10%).
  - Each new word stays on screen for ≥ 2 s, and the `KineticTitle` highlight marks the new word.
  - **Stress marks (Russian):** U+0301 on the stressed vowel of a new word, in both the VO and the on-screen text. edge-tts and Piper both use the mark when speaking (measured: the audio changes per mark), captions show it, and the QA transcript check ignores it.
  - Translations inside a line are voiced natively per language automatically (`make_voiceover.py` mixed voices). Write each word in its own script, or use `[[en:Hi]]` markup.
  - A female voice is `ru-RU-SvetlanaNeural` (edge); its offline Piper fallback is `ru_RU-irina-medium`, picked automatically.
- **The user adds topics later:** reuse `bible.md` and append episodes to `series.json`. Never rewrite earlier episodes unless asked.
