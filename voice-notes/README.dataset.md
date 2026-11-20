---
pretty_name: Taxonomy of AI Voice Notes
license: other
tags: [voice-notes, taxonomy]
configs:
- config_name: reviews
  default: true
  data_files: reviews/*.jsonl
- config_name: notes
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
| `reviews/<session>.jsonl` | review Space records, append-only, latest per `(task, model_id)` wins: `id`, `model_id`, `task`, `status` (`reviewed` = looked at, no note; `noted`; `note-failed`), `reviewed_at`, `annotator`, `audio`, `transcript`, `note` (`summary`, `verdict`, `reasons`, `subcategory`, `secondary`, `use_cases`, `mentioned_models`, `follow_up`), `asr` (`model`, `cost`) |
| `notes.jsonl` | one row per note: `id`, `recorded`, `task`, `audio`, `transcript`, `asr`, `added`, `processed_into` (subcategory ids), `processed_at` |

`reviews/` (with its audio and transcripts) is written by the review Space `danielrosehill/Taxonomy-Of-AI-Annotator`
(`space/` in the repo); `notes.jsonl` by `scripts/voice_note.py`.
