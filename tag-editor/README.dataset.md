---
license: cc-by-4.0
pretty_name: Hugging Face Model Tags (Curated)
tags: [hugging-face-hub, tags, metadata, taxonomy]
size_categories: [100K<n<1M]
configs:
- config_name: tag_groups
  default: true
  data_files: data/tag_groups.parquet
- config_name: base
  data_files: base/tag_groups.parquet
---

# Hugging Face Model Tags (Curated)

A hand-cleaned copy of the `tag_groups` config of
[`danielrosehill/HF-Model-Tags`](https://huggingface.co/datasets/danielrosehill/HF-Model-Tags) (snapshot 2026-11-15:
every tag on every Hub model, deduplicated into 439,946 groups). The raw dataset stays as it was; edits happen here.

| Path | What |
|---|---|
| `data/tag_groups.parquet` | Curated table (default config): the base minus deleted groups. Same columns as the base. |
| `base/tag_groups.parquet` | Frozen copy of the raw snapshot, never edited. |
| `edits/edits.jsonl` | Append-only edit log, one op per line: `{"op": "delete" \| "restore", "tag": "<group tag>", "at": "<UTC ISO time>"}`. The last op for a tag wins. |

Columns: see the raw dataset's card (`tag`, `kind`, `model_count`, downloads, `top_pipeline_tag`, `n_variants`,
`merge`, `variants`). Edits are made in a private editor Space; code is in
[Taxonomy of AI](https://github.com/danielrosehill/Taxonomy-Of-AI) (`tag-editor/`).
