---
title: HF Tag Explorer
emoji: 🔖
colorFrom: yellow
colorTo: blue
sdk: static
pinned: false
license: cc-by-4.0
short_description: Every Hugging Face model tag, deduplicated and browsable
datasets:
- danielrosehill/HF-Model-Tags
---

Browse every tag on Hugging Face models, deduplicated: spellings merged by case and separators,
singular/plural and -ing/-ed, and onto official Hub tags (13 spellings of `text-to-speech` are one row).
Filter by kind, pipeline and minimum model count; hide individual tags or the top N most used ones
(hidden tags are kept in your browser's localStorage; export/import as JSON).

Data: [`danielrosehill/HF-Model-Tags`](https://huggingface.co/datasets/danielrosehill/HF-Model-Tags), config `tag_groups`.
Source code and build: [Taxonomy of AI](https://github.com/danielrosehill/Taxonomy-Of-AI) (`tag-explorer/`,
`scripts/dedup_hub_tags.py`, `scripts/build_tag_explorer.py`).
