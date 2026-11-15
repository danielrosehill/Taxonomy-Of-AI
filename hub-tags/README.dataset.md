---
license: cc-by-4.0
pretty_name: Hugging Face Model Tags
tags: [hugging-face-hub, tags, metadata, taxonomy]
size_categories: [100K<n<1M]
configs:
- config_name: tags
  default: true
  data_files: snapshots/2026-11-15/tags.parquet
- config_name: freeform_folded
  data_files: snapshots/2026-11-15/freeform_folded.parquet
- config_name: tag_groups
  data_files: snapshots/2026-11-15/tag_groups.parquet
- config_name: kinds
  data_files: snapshots/2026-11-15/kinds.parquet
---

# Hugging Face Model Tags

Every distinct tag on every model on the Hugging Face Hub, deduplicated, with how many models use it.
Snapshot of **2026-11-15**: 3,239,126 models, **456,200 distinct tags**, of which 135,741 are freeform
(author-chosen) tags; 73,158 freeform tags are used by exactly one model.

Built for [Taxonomy of AI](https://github.com/danielrosehill/Taxonomy-Of-AI): authors' own tags are a
crowd-sourced classification of models, noisy but rich, and this makes the whole vocabulary queryable.

## Configs

**`tags`**: one row per distinct tag (exact string, case-sensitive).

| Column | Meaning |
|---|---|
| `tag` | the tag as it appears in a model's `tags` list |
| `kind` | the Hub's official tag type if the tag is in `GET /api/models-tags-by-type` (`language`, `library`, `license`, `region`, `pipeline_tag`, `dataset`, `deploy`, `other`, `bucket`); else the prefix before `:` when 50+ distinct tags share it (`base_model`, `arxiv`, `doi`, ...); else `freeform` |
| `model_count` | models carrying the tag |
| `downloads_30d`, `downloads_all_time` | summed over those models |
| `top_pipeline_tag` | the `pipeline_tag` most common among those models (models without one are ignored) |
| `top_pipeline_share` | models with that pipeline tag / `model_count` (low when most of the tag's models have no pipeline tag) |

**`freeform_folded`**: freeform tags merged across case and separators, so `voice-conversion`, `Voice Conversion`,
`voice_conversion` and `VoiceConversion` are one row. Columns: `key` (lowercased, letters and digits only),
`most_common` (the most-used spelling), `model_count` (sum over variants; a model tagged with two variants counts
twice), `n_variants`, `variants` (spellings, most used first).

**`tag_groups`**: all tags deduplicated into groups (added 2026-11-16; 439,946 groups). `tag` names the group: the
official tag if one is a member, else the most-used spelling. `kind` is that tag's kind. `model_count`, `downloads_30d`,
`downloads_all_time` are summed over members (a model tagged with two spellings counts twice). `n_variants`,
`variants` (`tag`, `kind`, `model_count`, most used first), `merge`: `none`, `fold` (case and separators), `official`
(a freeform spelling of an official tag joined it, e.g. 13 spellings of `text-to-speech`), `stem` (plural and
-ing/-ed forms, e.g. `fine-tuned` / `finetune` / `fine_tuning`). Model names with digits aren't stemmed; ID kinds
(`base_model`, `dataset`, `arxiv`, ...) aren't merged. Code: `scripts/dedup_hub_tags.py`. Browse it in the
[HF Tag Explorer](https://huggingface.co/spaces/danielrosehill/HF-Tag-Explorer) Space.

**`kinds`**: distinct tags and total taggings per `kind`.

## Source and method

- Source: [`cfahlgren1/hub-stats`](https://huggingface.co/datasets/cfahlgren1/hub-stats) `models.parquet`
  (updated 2026-11-15T13:41Z), which mirrors the Hub's model API. Only `id`, `tags`, `pipeline_tag` and download
  columns are read. Official tag types from `https://huggingface.co/api/models-tags-by-type` on the same day.
- Code: [`scripts/build_hub_tags.py`](https://github.com/danielrosehill/Taxonomy-Of-AI/blob/master/scripts/build_hub_tags.py)
  (DuckDB). Run on a Google Colab CPU VM in about a minute.
- Querying the Hub by tag: the website's `?other=<tag>` filter corresponds to `GET /api/models?filter=<tag>`
  (exact, case-sensitive). The API silently ignores an `other=` parameter.

New snapshots go in `snapshots/<date>/`; the configs point at the latest one.
