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
3. **Labels**, model by model, from a private annotation Space.
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
| `space/` | Annotation Space app (Gradio). |
| `scripts/build_hub_tags.py`, `hub-tags/` | Hub-wide tag inventory, published as `danielrosehill/HF-Model-Tags` (`hub-tags/out/` is gitignored). |
| `.claude/skills/task-taxonomy/` | Repo-level Claude Code skill for adding subcategories. |

## On the Hub

| Repo | Visibility | Contents |
|---|---|---|
| [`danielrosehill/Taxonomy-Of-AI`](https://huggingface.co/datasets/danielrosehill/Taxonomy-Of-AI) | public dataset | `taxonomy/<task>.json`, `labels/<task>.seed.jsonl`, reviewed labels as they're exported |
| `danielrosehill/Taxonomy-Of-AI-Working` | private dataset | `queue/<task>.jsonl` (models to label, most downloaded first, with tag-based suggestions), `annotations/` from the Space |
| `danielrosehill/Taxonomy-Of-AI-Annotator` | private Space | one model at a time with its card, one button per subcategory |

## Hub-wide sources (for later tasks and the classifier)

Checked 2026-11-15, both updated daily:

- [`cfahlgren1/hub-stats`](https://huggingface.co/datasets/cfahlgren1/hub-stats): `models.parquet` with metadata, including tags, for every model on the Hub (1.7 GB, so process it off-laptop).
- [`librarian-bots/model_cards_with_metadata`](https://huggingface.co/datasets/librarian-bots/model_cards_with_metadata): model card text plus metadata, 6 parquet shards.

## Freeform tags as evidence

Model authors' own tags are a classification already, if a noisy one. Each model's API record has them in its `tags` list. The website's `?other=<tag>` filter corresponds to `GET /api/models?filter=<tag>` (exact and case-sensitive: `voice-conversion` 209 models, `Voice Conversion` 19). The API **silently ignores** an `other=` parameter and returns unfiltered models (checked 2026-11-15; an earlier version of this README got this wrong). `GET /api/models-tags-by-type` lists only the official tag vocabulary (languages, libraries, licenses, pipeline tags, 8 `other` tags), so freeform tags have to be aggregated from model records.

That aggregation is published as [`danielrosehill/HF-Model-Tags`](https://huggingface.co/datasets/danielrosehill/HF-Model-Tags): every distinct tag on the Hub on 2026-11-15 (456,200 tags over 3,239,126 models; 135,741 freeform), each with its model count, downloads, official type and most common pipeline tag, plus a `freeform_folded` config that merges spellings (`voice-conversion` / `Voice Conversion` / `VoiceConversion` and three more: 241 models). Built by `scripts/build_hub_tags.py` on a Google Colab CPU VM (about a minute; via the private `data-notebooks` route on the home server). The dataset card is `hub-tags/README.dataset.md`.
