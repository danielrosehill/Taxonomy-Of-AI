---
pretty_name: Taxonomy of AI Voice Notes
license: other
tags: [voice-notes, taxonomy]
configs:
- config_name: notes
  default: true
  data_files: notes.jsonl
---

# Taxonomy of AI: voice notes (private)

Voice notes recorded while sorting Hugging Face models into the subcategories of
[Taxonomy of AI](https://github.com/danielrosehill/Taxonomy-Of-AI), with their raw transcripts. The repo's
`notes-to-taxonomy` skill turns each note into taxonomy entries and records which ones in `processed_into`.

| Path | What |
|---|---|
| `audio/<YYYY-MM-DD>/<id>.<ext>` | the recording, unchanged |
| `transcripts/<YYYY-MM-DD>/<id>.md` | raw ASR transcript, front matter `id`, `recorded`, `task`, `asr` |
| `notes.jsonl` | one row per note: `id`, `recorded`, `task`, `audio`, `transcript`, `asr`, `added`, `processed_into` (subcategory ids), `processed_at` |

Written by `scripts/voice_note.py` in the repo.
