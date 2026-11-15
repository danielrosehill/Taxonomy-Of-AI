---
title: HF Tag Editor
emoji: ✂️
colorFrom: red
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
---

Private editor for [`danielrosehill/HF-Model-Tags-Curated`](https://huggingface.co/datasets/danielrosehill/HF-Model-Tags-Curated).
Sort (most used, A→Z, Z→A, least used), filter, delete or restore tag groups, undo, then Save: one commit that appends
to `edits/edits.jsonl` and rebuilds `data/tag_groups.parquet` (base minus deleted). Needs the `HF_TOKEN` secret.
Source: [Taxonomy of AI](https://github.com/danielrosehill/Taxonomy-Of-AI) `tag-editor/`.
