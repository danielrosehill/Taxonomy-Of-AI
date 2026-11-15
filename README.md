# HF-A2A-Analysis

Analysis of the **audio-to-audio** models on Hugging Face (`pipeline_tag=audio-to-audio`, the set listed at <https://huggingface.co/models?pipeline_tag=audio-to-audio>).

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
