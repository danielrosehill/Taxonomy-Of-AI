# audio-to-audio

Hugging Face models with `pipeline_tag=audio-to-audio` (<https://huggingface.co/models?pipeline_tag=audio-to-audio>). The first task in [Taxonomy of AI](../../README.md).

## Step 1: model inventory (done 2026-11-15)

`data/` (this folder) holds a snapshot of every audio-to-audio model's metadata from the public Hub API.

| File | Contents |
|---|---|
| `data/models.json` | `{meta, models}`: full API record per model, with every `expand[]` field the endpoint accepts (card data, config, tags, siblings/files, spaces, safetensors params, downloads, likes, dates, gating, inference providers, ...). `meta.fetched_at` is the snapshot time. |
| `data/models.csv` | One row per model: id, author, created_at, last_modified, downloads_30d, downloads_all_time, likes, trending_score, library_name, license, languages (from model card), base_models, arxiv, gated, disabled, params (safetensors total), file_count, spaces_count, tags. |

Snapshot 2026-11-15T16:43Z: **1,887 models**, equal to the `numTotalItems` the website reports for the same filter (verified).

### Refresh

```bash
uv run scripts/fetch_task_models.py audio-to-audio   # from the repo root
```

No auth, stdlib only. Notes for whoever runs it next:

- Endpoint: `GET https://huggingface.co/api/models?pipeline_tag=audio-to-audio&limit=1000&expand[]=...`. Pagination is cursor-based through the `Link: <...>; rel="next"` response header; there is no total-count field in the API response.
- Passing an unknown `expand[]` value returns a 400 listing the accepted values; that is how the `EXPAND` list in the script was built. If HF adds fields, run once with a bogus value to see the new list.
- `downloads` is the last 30 days; `downloadsAllTime` is the lifetime count.
- `createdAt` is the repo creation date, the nearest thing the API has to a release date. Repos that predate HF tracking it carry the placeholder `2022-03-02T23:29:...` (56 models in the 2026-11-15 snapshot); treat that date as "on or before March 2022", not a release date.
- Languages come from the model card's `language` field, not tags (short tags like `rvc`/`svc` look like ISO codes).

## Step 2: unofficial taxonomy (started 2026-11-15)

`taxonomy.json` (this folder) holds the subcategories, each with a definition, use cases, example models and the metadata signals (tags, library) that identify its members. Entries are added with the repo-level Claude Code skill [`task-taxonomy`](../../.claude/skills/task-taxonomy/SKILL.md): name a subcategory and give example models, and the skill resolves them against `data/models.json`, writes the entry and regenerates the table below.

<!-- taxonomy:start -->
| Subcategory | Definition | Examples | Tag-signal matches |
|---|---|---|---|
| Speech restoration (universal cleanup) | Degraded speech in, clean speech out, recovering lost signal instead of only subtracting noise. The user's framing: a predictive approach that improves the audio, where older reductive denoisers lose speaker fidelity. | [`nvidia/NVIDIA-NemotronLabs-RE-USE`](https://huggingface.co/nvidia/NVIDIA-NemotronLabs-RE-USE) | 48 |
| Speaker isolation (target speaker extraction) | Mixed audio in, only the target speaker out, removing other voices as well as noise. Narrower than general cleanup; replaces earlier cruder heuristic approaches. | [`arbazsiddiqui/voxlock`](https://huggingface.co/arbazsiddiqui/voxlock) | 15 |
| Speech enhancement and denoising | General-purpose speech improvement: noise suppression, denoising, dereverberation. | [`desert-ant-labs/clear`](https://huggingface.co/desert-ant-labs/clear) | 183 |
| Stem separation | A music mix in, separate stems out (vocals, drums, bass, other). | [`iBoostAI/Demucs-v4`](https://huggingface.co/iBoostAI/Demucs-v4) | 153 |
| Instruction-guided audio editing | Audio plus a natural-language instruction in, edited audio out. The user flags this as a very unusual entry in the category. | [`GeWu-Lab/SteerSound`](https://huggingface.co/GeWu-Lab/SteerSound) | 7 |
| Voice conversion | Speech or singing in one voice in, the same content in another voice out. | [`IAHispano/Applio`](https://huggingface.co/IAHispano/Applio) | 399 |

Match counts are estimates (models carrying at least one of the subcategory's tags) and overlap. Details in `taxonomy.json`.
<!-- taxonomy:end -->
