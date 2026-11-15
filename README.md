# Taxonomy of AI

My own classification of AI models on Hugging Face, task by task. The Hub sorts models by `pipeline_tag`; I sort them by what they are actually for. It's a personal taxonomy, and no one else has to agree with it.

## Why this exists (written 2026-11-15)

**Everything here is dated 2026-11-15.** This category moves quickly, and most of what I note today will be out of date almost immediately. Read it as a snapshot of one day, not a current survey.

I've been interested in ASR and dictation for a long time, and I've been fine-tuning NVIDIA Parakeet ASR models myself:

- [Hebrish](https://huggingface.co/Hebrish): Parakeet fine-tunes for English spoken with Hebrew-speaker accents and Hebrew-English code-switching.
- [Fritter](https://huggingface.co/danielrosehill/Fritter): a Parakeet TDT 0.6B v2 fine-tune for English tech dictation ([demo](https://huggingface.co/spaces/danielrosehill/Fritter-Demo)).

That work led me to audio-to-audio, the first task here, which is getting interesting, especially the small accessory models that sit around an ASR or voice pipeline: denoising, enhancement, separation, voice conversion and so on.

My view is that Hugging Face's task labels, each one a traditionally delineated ML task, hide a whole world of very different use cases underneath. `audio-to-audio` is one label covering singing-voice conversion, speech enhancement, music stem separation, codecs and much more, and those have little in common beyond audio going in and audio coming out.

I keep a lot of Hugging Face collections, but they're mostly for my own use: whenever I look for models for a specific task, I end up with my own informal ways of breaking the task down. This repo writes that breakdown down.

So this project is:

1. **A snapshot per task** of every model the Hub lists under that `pipeline_tag` (`tasks/<task>/data/`).
2. **An unofficial taxonomy per task**, built with Claude: I give examples of what I see as the canonical subcategories, and Claude records them against the snapshot (`tasks/<task>/taxonomy.json`).
3. **Labels**, model by model, in Carrot Cake Lab (Label Studio project 34, since 2026-11-15; the `space/` annotator was never deployed).
4. **Later, a classifier** trained on those labels, so new models can be sorted by my rubric automatically.

It's a personal notebook, kept public in case it's useful to others interested in these tasks.

## Tasks

| Task | Snapshot | Subcategories | Notes |
|---|---|---|---|
| [audio-to-audio](tasks/audio-to-audio/README.md) | 1,887 models, 2026-11-15 | 6 | first task |

## Layout

| Path | What |
|---|---|
| `tasks/<task>/data/models.json`, `models.csv` | Hub snapshot for the task (`uv run scripts/fetch_task_models.py <task>`). |
| `tasks/<task>/taxonomy.json` | Subcategories: definition, use cases, example models, tag signals. Source of truth. |
| `scripts/sync_hf_datasets.py` | Pushes a task's taxonomy, queue and seed labels to the Hub datasets. |
| `space/` | Annotation Space app (Gradio). Not deployed; its queue, labels and record format now run in Label Studio. |
| `scripts/ls_build_tasks.py`, `scripts/ls_export.py` | Queue -> Label Studio tasks; Label Studio labels -> `annotations/` (see below). |
| `scripts/build_hub_tags.py`, `hub-tags/` | Hub-wide tag inventory, published as `danielrosehill/HF-Model-Tags` (`hub-tags/out/` is gitignored). |
| `scripts/dedup_hub_tags.py` | Second-pass tag dedup: `tags.parquet` -> `tag_groups.parquet` (fold, official, stem merges). Local, ~8 s. |
| `scripts/build_tag_explorer.py`, `tag-explorer/` | Static Space [`danielrosehill/HF-Tag-Explorer`](https://huggingface.co/spaces/danielrosehill/HF-Tag-Explorer): browse tag groups, hide tags or the top N most used. `--publish` uploads Space + dataset file. |
| `tag-editor/`, `scripts/seed_curated_tags.py` | Private Docker Space [`danielrosehill/HF-Tag-Editor`](https://huggingface.co/spaces/danielrosehill/HF-Tag-Editor): sort (A→Z, most used, ...), filter, delete/restore tag groups, Save commits to `danielrosehill/HF-Model-Tags-Curated`. |
| `scripts/voice_note.py`, `voice-notes/` | Voice notes + raw transcripts into the private dataset `danielrosehill/Taxonomy-Of-AI-Voice-Notes`. |
| `.claude/skills/task-taxonomy/` | Repo-level Claude Code skill for adding subcategories. |
| `.claude/skills/notes-to-taxonomy/` | Repo-level skill: freeform notes or a voice recording -> subcategories, via `task-taxonomy`. |

## On the Hub

| Repo | Visibility | Contents |
|---|---|---|
| [`danielrosehill/Taxonomy-Of-AI`](https://huggingface.co/datasets/danielrosehill/Taxonomy-Of-AI) | public dataset | `taxonomy/<task>.json`, `labels/<task>.seed.jsonl`, reviewed labels as they're exported |
| `danielrosehill/Taxonomy-Of-AI-Working` | private dataset | `queue/<task>.jsonl` (models to label, most downloaded first, with tag-based suggestions), `annotations/` (Space record format; written by `scripts/ls_export.py`) |
| `danielrosehill/Taxonomy-Of-AI-Annotator` | private Space | one model at a time with its card, one button per subcategory |

## Labelling in Carrot Cake Lab (since 2026-11-15)

Project 34 "Taxonomy of AI: audio-to-audio": https://carrotcakelab.com/projects/34 (Label Studio, residencehome; API on
the LAN at http://10.0.0.2:8140). Same queue order (most downloaded first), same buttons as `space/app.py`: keys 1-6 for
the subcategories, 0 new category (typed id -> `new:<id>`), 7 unsure, 8 misc, 9 not audio-to-audio, "Also fits" for
`secondary`, notes. The tag-signal `suggested` subcategories are pre-selected as a prediction (`tag-signal`).

```bash
with-secrets uv run scripts/ls_build_tasks.py audio-to-audio --start 15 --n 100 -o /tmp/toa/tasks.json  # next batch, card text fetched
with-secrets python3 -I <Carrot-Cake-Lab-Plugin>/scripts/ccl.py import 34 /tmp/toa/tasks.json --confirm
with-secrets uv run scripts/ls_export.py --out /tmp/toa-export [--push]   # -> annotations/<ts>-ls34.jsonl
```

The export writes the Space's record exactly (`model_id, task, subcategory, secondary, source, annotator, labeled_at,
notes`); checked 2026-11-15 on synthetic annotations only (no labels existed yet). `--start` counts unlabelled models,
so after an export, start at 0 again and the builder skips what is in `annotations/` (tasks still in Label Studio
but not exported would be duplicated: export first).

## Hub-wide sources (for later tasks and the classifier)

Checked 2026-11-15, both updated daily:

- [`cfahlgren1/hub-stats`](https://huggingface.co/datasets/cfahlgren1/hub-stats): `models.parquet` with metadata, including tags, for every model on the Hub (1.7 GB, so process it off-laptop).
- [`librarian-bots/model_cards_with_metadata`](https://huggingface.co/datasets/librarian-bots/model_cards_with_metadata): model card text plus metadata, 6 parquet shards.

## Freeform tags as evidence

Model authors' own tags are a classification already, if a noisy one. Each model's API record has them in its `tags` list. The website's `?other=<tag>` filter corresponds to `GET /api/models?filter=<tag>` (exact and case-sensitive: `voice-conversion` 209 models, `Voice Conversion` 19). The API **silently ignores** an `other=` parameter and returns unfiltered models (checked 2026-11-15; an earlier version of this README got this wrong). `GET /api/models-tags-by-type` lists only the official tag vocabulary (languages, libraries, licenses, pipeline tags, 8 `other` tags), so freeform tags have to be aggregated from model records.

That aggregation is published as [`danielrosehill/HF-Model-Tags`](https://huggingface.co/datasets/danielrosehill/HF-Model-Tags): every distinct tag on the Hub on 2026-11-15 (456,200 tags over 3,239,126 models; 135,741 freeform), each with its model count, downloads, official type and most common pipeline tag, plus a `freeform_folded` config that merges spellings (`voice-conversion` / `Voice Conversion` / `VoiceConversion` and three more: 241 models). Built by `scripts/build_hub_tags.py` on a Google Colab CPU VM (about a minute; via the private `data-notebooks` route on the home server). The dataset card is `hub-tags/README.dataset.md`.

**Deduplication, second pass (2026-11-16).** `scripts/dedup_hub_tags.py` groups the 456,200 tag strings into 439,946 tag groups (config `tag_groups`); freeform groups drop from 135,741 strings to 119,488 groups, against 122,367 with case/separator folding alone. Three merges, recorded per group in `merge`: `fold` (case and separators), `official` (a freeform spelling of an official tag joins it: 13 spellings of `text-to-speech`, 532 groups), `stem` (plural -s/-es/-ies, -ing/-ed on 8+ letters, a vowel-consonant final -e: `fine-tuned` absorbs 29 spellings incl. `finetune`, `fine_tuning`; 2,232 groups). Keys with digits (model names) aren't stemmed; `STEM_EXCEPTIONS` holds words where stemming is wrong (`news`, `physics`, `embed`). Known over-merges, accepted: `falcon` + `falcon-e`, `custom` + `custome`. Counts are summed over spellings (taggings, not distinct models). ID kinds (`base_model:`, `dataset:`, `arxiv:`) are not merged.

**Curated copy (2026-11-16).** The raw `HF-Model-Tags` stays a static artifact. Cleaning happens in the public dataset [`danielrosehill/HF-Model-Tags-Curated`](https://huggingface.co/datasets/danielrosehill/HF-Model-Tags-Curated): `base/tag_groups.parquet` (frozen copy), `edits/edits.jsonl` (append-only `{op: delete|restore, tag, at}`, last op per tag wins), `data/tag_groups.parquet` (base minus deleted; default config). The private Space `HF-Tag-Editor` (FastAPI + one HTML page, `tag-editor/`, secret `HF_TOKEN`) loads the 125,348 semantic-kind groups and writes both files in one commit per Save. Only delete/restore exist so far; new ops (rename, merge) go in `OPS` in `tag-editor/app.py` plus the materialise step. The private Space's `*.hf.space` URL answers 404 without an HF token: open it from huggingface.co while logged in.

All of these are in the private collection **Taxonomy of AI (Personal)**: <https://huggingface.co/collections/danielrosehill/taxonomy-of-ai-personal-6afa3e43a7a31348025a7f98>.

[HF Tag Explorer](https://huggingface.co/spaces/danielrosehill/HF-Tag-Explorer) (static Space, `tag-explorer/`) shows the 53,776 groups on 3+ models (ID kinds on 25+): search across spellings, filter by kind and pipeline, hide tags one by one or the top N most used (kept in localStorage, exportable as JSON). Rebuild: `uv run scripts/dedup_hub_tags.py && uv run scripts/build_tag_explorer.py --publish`.
