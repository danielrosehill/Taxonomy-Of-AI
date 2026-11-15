# /// script
# requires-python = ">=3.11"
# dependencies = ["duckdb>=1.1", "huggingface_hub>=0.30"]
# ///
"""Build the Tag Explorer Space's data from hub-tags/out/tag_groups.parquet, optionally publish.

Usage:
  uv run scripts/build_tag_explorer.py             -> tag-explorer/data.json
  uv run scripts/build_tag_explorer.py --publish   -> also uploads tag_groups.parquet + card to the
                                                      danielrosehill/HF-Model-Tags dataset and tag-explorer/
                                                      to the danielrosehill/HF-Tag-Explorer Space (static)

Run scripts/dedup_hub_tags.py first. Included rows: tag groups of semantic kinds (freeform, pipeline_tag,
library, license, language, ...) used by MIN_SEMANTIC+ models, and ID-like kinds (base_model, dataset, arxiv,
...) used by MIN_ID+ models. The full table stays in the dataset.
"""
import json, sys
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "hub-tags" / "out"
SPACE = ROOT / "tag-explorer"
DATASET, SPACE_ID = "danielrosehill/HF-Model-Tags", "danielrosehill/HF-Tag-Explorer"
SEMANTIC = ("freeform", "pipeline_tag", "library", "license", "language", "region", "other", "deploy", "bucket")
MIN_SEMANTIC, MIN_ID, MAX_VARIANTS = 3, 25, 12

summary = json.loads((OUT / "summary.json").read_text())
snapshot = summary["built_at"][:10]
rows = duckdb.sql(f"""
  SELECT tag, kind, model_count, downloads_30d, coalesce(top_pipeline_tag, ''), n_variants, merge,
         [v.tag || '\t' || v.model_count FOR v IN variants][1:{MAX_VARIANTS}]
  FROM '{OUT}/tag_groups.parquet'
  WHERE (kind IN {SEMANTIC} AND model_count >= {MIN_SEMANTIC}) OR (kind NOT IN {SEMANTIC} AND model_count >= {MIN_ID})
  ORDER BY model_count DESC""").fetchall()

kinds = sorted({r[1] for r in rows}, key=lambda k: (k not in SEMANTIC, k))
pipes = sorted({r[4] for r in rows})
merges = ["none", "fold", "official", "stem"]
data = {
    "snapshot": snapshot, "source": summary["source"], "dataset": DATASET,
    "totals": {"models": summary["models"], "distinct_tags": summary["distinct_tags"], **summary["dedup"]},
    "thresholds": {"semantic_min_models": MIN_SEMANTIC, "id_min_models": MIN_ID},
    "semantic_kinds": list(SEMANTIC), "kinds": kinds, "pipelines": pipes, "merges": merges,
    # one row: [tag, kind idx, models (taggings), downloads 30d, pipeline idx, n variants, merge idx, "variant\tcount", ...]
    "rows": [[r[0], kinds.index(r[1]), r[2], r[3], pipes.index(r[4]), r[5], merges.index(r[6]), *(r[7] if r[5] > 1 else [])]
             for r in rows],
}
SPACE.mkdir(exist_ok=True)
(SPACE / "data.json").write_text(json.dumps(data, separators=(",", ":"), ensure_ascii=False))
print(f"{len(rows):,} rows -> {SPACE / 'data.json'} ({(SPACE / 'data.json').stat().st_size / 1e6:.1f} MB)")

if "--publish" in sys.argv:
    from huggingface_hub import HfApi
    api = HfApi()
    api.upload_file(path_or_fileobj=OUT / "tag_groups.parquet", path_in_repo=f"snapshots/{snapshot}/tag_groups.parquet",
                    repo_id=DATASET, repo_type="dataset", commit_message=f"tag_groups for {snapshot}")
    api.upload_file(path_or_fileobj=ROOT / "hub-tags" / "README.dataset.md", path_in_repo="README.md",
                    repo_id=DATASET, repo_type="dataset", commit_message="Card: tag_groups config")
    api.create_repo(SPACE_ID, repo_type="space", space_sdk="static", private=False, exist_ok=True)
    api.upload_folder(folder_path=SPACE, repo_id=SPACE_ID, repo_type="space", commit_message=f"Data {snapshot}")
    print(f"https://huggingface.co/datasets/{DATASET}\nhttps://huggingface.co/spaces/{SPACE_ID}")
