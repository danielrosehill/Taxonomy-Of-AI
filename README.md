# HF-A2A-Analysis

Analysis of the **audio-to-audio** models on Hugging Face (`pipeline_tag=audio-to-audio`, the set listed at <https://huggingface.co/models?pipeline_tag=audio-to-audio>).

## Why this exists (written 2026-11-15)

**Everything here is dated 2026-11-15.** This category moves quickly, and most of what I note today will be out of date almost immediately. Read it as a snapshot of one day, not a current survey.

I've been interested in ASR and dictation for a long time, and I've been fine-tuning NVIDIA Parakeet ASR models myself:

- [Hebrish](https://huggingface.co/Hebrish): Parakeet fine-tunes for English spoken with Hebrew-speaker accents and Hebrew-English code-switching.
- [Fritter](https://huggingface.co/danielrosehill/Fritter): a Parakeet TDT 0.6B v2 fine-tune for English tech dictation ([demo](https://huggingface.co/spaces/danielrosehill/Fritter-Demo)).

That work led me to audio-to-audio, which is getting interesting, especially the small accessory models that sit around an ASR or voice pipeline: denoising, enhancement, separation, voice conversion and so on.

My view is that Hugging Face's task labels, each one a traditionally delineated ML task, hide a whole world of very different use cases underneath. `audio-to-audio` is one label covering singing-voice conversion, speech enhancement, music stem separation, codecs and much more, and those have little in common beyond audio going in and audio coming out.

So this repo is:

1. **A one-time import** of every audio-to-audio model on the Hub (Step 1 below).
2. **An unofficial taxonomy**, built with Claude: I give examples of what I see as the canonical subcategories and Claude records them against the snapshot (Step 2 below).

It's a personal notebook, kept public in case it's useful to others interested in audio-to-audio or one of its specific tasks.

## Step 1: model inventory (done 2026-11-15)

`data/` holds a snapshot of every audio-to-audio model's metadata from the public Hub API.

| File | Contents |
|---|---|
| `data/models.json` | `{meta, models}`: full API record per model, with every `expand[]` field the endpoint accepts (card data, config, tags, siblings/files, spaces, safetensors params, downloads, likes, dates, gating, inference providers, ...). `meta.fetched_at` is the snapshot time. |
| `data/models.csv` | One row per model: id, author, created_at, last_modified, downloads_30d, downloads_all_time, likes, trending_score, library_name, license, languages (from model card), base_models, arxiv, gated, disabled, params (safetensors total), file_count, spaces_count, tags. |

Snapshot 2026-11-15T16:43Z: **1,887 models**, equal to the `numTotalItems` the website reports for the same filter (verified).

### Refresh

```bash
uv run scripts/fetch_models.py
```

No auth, stdlib only. Notes for whoever runs it next:

- Endpoint: `GET https://huggingface.co/api/models?pipeline_tag=audio-to-audio&limit=1000&expand[]=...`. Pagination is cursor-based through the `Link: <...>; rel="next"` response header; there is no total-count field in the API response.
- Passing an unknown `expand[]` value returns a 400 listing the accepted values; that is how the `EXPAND` list in the script was built. If HF adds fields, run once with a bogus value to see the new list.
- `downloads` is the last 30 days; `downloadsAllTime` is the lifetime count.
- `createdAt` is the repo creation date, the nearest thing the API has to a release date. Repos that predate HF tracking it carry the placeholder `2022-03-02T23:29:...` (56 models in the 2026-11-15 snapshot); treat that date as "on or before March 2022", not a release date.
- Languages come from the model card's `language` field, not tags (short tags like `rvc`/`svc` look like ISO codes).

## Step 2: unofficial taxonomy (started 2026-11-15)

`taxonomy/taxonomy.json` holds the subcategories, each with a definition, use cases, example models and the metadata signals (tags, library) that identify its members. Entries are added with the repo-level Claude Code skill [`.claude/skills/a2a-taxonomy/SKILL.md`](.claude/skills/a2a-taxonomy/SKILL.md): name a subcategory and give example models, and the skill resolves them against `data/models.json`, writes the entry and regenerates the table below.

<!-- taxonomy:start -->
_No subcategories yet._
<!-- taxonomy:end -->
