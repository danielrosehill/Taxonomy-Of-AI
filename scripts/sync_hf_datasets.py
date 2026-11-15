# /// script
# requires-python = ">=3.11"
# dependencies = ["huggingface_hub>=1.0"]
# ///
"""Push a task's taxonomy, annotation queue and seed labels to the Hugging Face datasets.

Usage: uv run scripts/sync_hf_datasets.py [task]      (default audio-to-audio)

  Public  danielrosehill/Taxonomy-Of-AI          taxonomy/<task>.json, labels/<task>.seed.jsonl
  Private danielrosehill/Taxonomy-Of-AI-Working  taxonomy/<task>.json, queue/<task>.jsonl
                                                          (annotations/ is written by the annotation Space)

Reads tasks/<task>/taxonomy.json and tasks/<task>/data/models.json. Auth: the cached `hf auth login` token.
Safe to re-run: it overwrites taxonomy and queue, never touches annotations/.
"""
import io, json, sys
from pathlib import Path
from huggingface_hub import HfApi, CommitOperationAdd

OWNER = "danielrosehill"
PUBLIC = f"{OWNER}/Taxonomy-Of-AI"
WORKING = f"{OWNER}/Taxonomy-Of-AI-Working"
ROOT = Path(__file__).resolve().parent.parent
task = sys.argv[1] if len(sys.argv) > 1 else "audio-to-audio"
tax = json.loads((ROOT / "tasks" / task / "taxonomy.json").read_text())
models = json.loads((ROOT / "tasks" / task / "data" / "models.json").read_text())["models"]
snapshot = tax["meta"]["snapshot"]


def suggestions(tags):
    low = {t.lower() for t in tags}
    return [s["id"] for s in tax["subcategories"] if low & {x.lower() for x in s.get("signal_tags", [])}]


queue = []
for m in sorted(models, key=lambda m: -(m.get("downloadsAllTime") or 0)):
    card = m.get("cardData") or {}
    queue.append({
        "model_id": m["id"], "task": task,
        "downloads_all_time": m.get("downloadsAllTime") or 0, "likes": m.get("likes") or 0,
        "created_at": m.get("createdAt"), "library_name": m.get("library_name") or card.get("library_name"),
        "license": card.get("license"), "tags": [t for t in m.get("tags", []) if ":" not in t],
        "suggested": suggestions(m.get("tags", [])),
    })

seed = [{"model_id": e["id"], "task": task, "subcategory": s["id"], "secondary": [],
         "source": "seed", "annotator": OWNER, "labeled_at": e["added"], "notes": e["note"]}
        for s in tax["subcategories"] for e in s["examples"]]

jl = lambda rows: "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows).encode()
tax_b = json.dumps(tax, indent=2, ensure_ascii=False).encode()

PUBLIC_CARD = f"""---
license: cc-by-4.0
pretty_name: Taxonomy of AI
tags: [model-classification, taxonomy, hugging-face-hub]
---
# Taxonomy of AI

One person's unofficial classification of Hugging Face models into use-case subcategories, task by task.
The Hub's `pipeline_tag` tasks each hide very different use cases; this dataset records a finer, personal breakdown.
No one else has to agree with it. Started 2026-11-15; categories in this space change fast, so everything is dated.

Source, rubrics and method: <https://github.com/danielrosehill/Taxonomy-Of-AI>

## Files

- `taxonomy/<task>.json`: subcategories for a task (definition, use cases, example models, tag signals).
- `labels/<task>.seed.jsonl`: the canonical example models, one label each.
- `labels/<task>.jsonl`: reviewed labels exported from annotation (added as annotation progresses).

Label fields: `model_id`, `task` (HF pipeline_tag), `subcategory` (taxonomy id), `secondary` (other ids that also fit),
`source` (`seed` | `annotation` | `classifier`), `annotator`, `labeled_at`, `notes`.

Tasks so far: `audio-to-audio` (snapshot of {len(models)} models, {snapshot.split('(')[-1].rstrip(')')}).
"""

WORKING_CARD = """---
license: cc-by-4.0
pretty_name: Taxonomy of AI (working)
---
# Taxonomy of AI: working set (private)

Annotation workspace behind `danielrosehill/Taxonomy-Of-AI`.

- `queue/<task>.jsonl`: models to label, most-downloaded first, with tag-signal `suggested` subcategories.
- `taxonomy/<task>.json`: categories shown as buttons in the annotation Space.
- `annotations/*.jsonl`: written by the Space `danielrosehill/Taxonomy-Of-AI-Annotator` (append-only;
  the latest record per `model_id` wins).

Pushed by `scripts/sync_hf_datasets.py` in <https://github.com/danielrosehill/Taxonomy-Of-AI>.
"""

api = HfApi()
api.create_repo(PUBLIC, repo_type="dataset", private=False, exist_ok=True)
api.create_repo(WORKING, repo_type="dataset", private=True, exist_ok=True)
add = lambda path, b: CommitOperationAdd(path_in_repo=path, path_or_fileobj=io.BytesIO(b))
api.create_commit(PUBLIC, repo_type="dataset", commit_message=f"sync {task}", operations=[
    add("README.md", PUBLIC_CARD.encode()), add(f"taxonomy/{task}.json", tax_b),
    add(f"labels/{task}.seed.jsonl", jl(seed))])
api.create_commit(WORKING, repo_type="dataset", commit_message=f"sync {task}", operations=[
    add("README.md", WORKING_CARD.encode()), add(f"taxonomy/{task}.json", tax_b),
    add(f"queue/{task}.jsonl", jl(queue))])
print(json.dumps({"task": task, "queue": len(queue), "seed_labels": len(seed),
                  "with_suggestion": sum(1 for q in queue if q["suggested"]), "public": PUBLIC, "working": WORKING}))
