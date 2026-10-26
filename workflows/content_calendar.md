# Workflow: Content calendar (plan a series, then make it)

## Objective
Turn "brand + period" into an approved list of video ideas, then produce them one by one with `make_video.md`. This is what makes the factory a factory: you approve the plan once, and each item becomes a brief that runs on its own.

## Inputs
| Input | Required | Default |
|---|---|---|
| Brand slug | yes | — (onboard first if it's missing) |
| Period | yes | 2 weeks |
| Posts per week | no | 3 |
| Platforms | no | from the brand (B2B: LinkedIn + Reels; consumer: Instagram) |
| Languages | no | the brand's main language(s) |
| Themes, launches, events | no | none. Events need a date, time + timezone and link |

## Steps
1. **Plan.** Spawn the `content-planner` agent with the inputs. It reads the profile, the playbook, `performance.md` and the existing `calendar.json`, and returns a rationale + JSON. If it lists `questions` that block an item, ask the user once (all questions in one message), or drop that item.
2. **Approve.** Show the user a compact table: date, goal, format, topic, hook, languages. This is the only approval for the series; the user can edit, drop or reorder items.
3. **Save the queue.** Write the approved items to `brands/<slug>/calendar.json`:
   - top level: `{"brand", "updated", "items": [...]}`
   - each item: the planner fields + `"status": "todo"` + `"runs": []`

   Merge with existing items; never delete made or posted ones.
4. **Make each item.** Go in date order, one at a time (the laptop's RAM can't run two renders). For every language in the item:
   - Run `workflows/make_video.md` from step 1, with the item as the brief: topic, goal, format, hook, facts, aspects, CTA.
   - The strategist may refine the hook but keeps the format and facts.
   - Add the run name to `runs`.
   - When every language has been delivered, set `"status": "made"`.
5. **Report.** After each item, tell the user its output folder(s). After the batch, list: made, skipped (and why), and the fallbacks used.
6. **Posted.** When the user says an item is posted, set `"status": "posted"` and `"posted_at"`. Two or three days later, run `workflows/review_performance.md` for it.

## Edge cases
- **Long batches.** Stories with local AI images take ~10 min per image. Plan them overnight, or run motion-graphics items first.
- **A fact changed** (a new number in profile.md): re-plan the affected `todo` items only.
- **Events.** Make the announcement ≥ 7 days before the event, and a reminder (shorter, 9x16) 1 day before.
- **The user wants a different mix:** pass it to the planner as an explicit rule.
