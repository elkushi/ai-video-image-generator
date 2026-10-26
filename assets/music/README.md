# Music library (royalty-free, free)

Drop tracks here and register each one in `music.json`. `tools/pick_music.py` picks the best mood match and rotates tracks so videos don't all sound the same. Without tracks, a soft built-in synth bed is generated instead.

Free sources whose licences allow commercial social use without attribution:
- Pixabay Music: https://pixabay.com/music/ (Pixabay Content License)
- YouTube Audio Library: https://studio.youtube.com, Audio Library (only use tracks marked "no attribution required" outside YouTube)

Aim for 2–4 tracks per mood: upbeat, corporate, inspiring, calm, dramatic, playful, tech.

`music.json` example:
```json
[
  {"file": "bright-future.mp3", "title": "Bright Future", "moods": ["upbeat", "corporate"], "seconds": 142,
   "license": "Pixabay Content License", "source": "https://pixabay.com/music/..."}
]
```
