# /// script
# requires-python = ">=3.11"
# dependencies = ["huggingface_hub>=0.30"]
# ///
"""Create the editable copy of the tag inventory: danielrosehill/HF-Model-Tags-Curated (public).

Usage: uv run scripts/seed_curated_tags.py        (once; refuses to overwrite an existing edit log)

Layout of the curated dataset:
  base/tag_groups.parquet   frozen copy of HF-Model-Tags snapshots/<date>/tag_groups.parquet (never edited)
  edits/edits.jsonl         append-only log written by the HF-Tag-Editor Space, one op per line:
                            {"op": "delete" | "restore", "tag": "<group tag>", "at": "<UTC ISO>"}
  data/tag_groups.parquet   base minus deleted groups, rebuilt by the Space on every save (the default config)

The raw dataset danielrosehill/HF-Model-Tags stays a static artifact.
"""
from pathlib import Path
from huggingface_hub import HfApi, CommitOperationAdd, hf_hub_download

RAW, CURATED, SNAPSHOT = "danielrosehill/HF-Model-Tags", "danielrosehill/HF-Model-Tags-Curated", "2026-11-15"
api = HfApi()
api.create_repo(CURATED, repo_type="dataset", private=False, exist_ok=True)
if api.file_exists(CURATED, "edits/edits.jsonl", repo_type="dataset"):
    raise SystemExit("edits/edits.jsonl exists: already seeded, not overwriting")
base = hf_hub_download(RAW, f"snapshots/{SNAPSHOT}/tag_groups.parquet", repo_type="dataset")
card = Path(__file__).resolve().parent.parent / "tag-editor" / "README.dataset.md"
api.create_commit(CURATED, repo_type="dataset", commit_message=f"Seed from {RAW} snapshot {SNAPSHOT}", operations=[
    CommitOperationAdd("base/tag_groups.parquet", base),
    CommitOperationAdd("data/tag_groups.parquet", base),
    CommitOperationAdd("edits/edits.jsonl", b""),
    CommitOperationAdd("README.md", str(card)),
])
print(f"https://huggingface.co/datasets/{CURATED}")
