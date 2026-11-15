"""HF Tag Editor: private Space for cleaning danielrosehill/HF-Model-Tags-Curated.

GET  /            the editor page (index.html)
GET  /api/rows    semantic-kind tag groups of the base + the current deleted set
POST /api/save    {"ops": [{"op": "delete"|"restore", "tag": "..."}]} -> appends to edits/edits.jsonl,
                  rebuilds data/tag_groups.parquet (base minus deleted), one commit to the dataset

Needs Space secret HF_TOKEN with write access to the dataset. Runs on the free CPU tier.
"""
import json, os, tempfile, threading
from datetime import datetime, timezone
from pathlib import Path
import duckdb
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from huggingface_hub import HfApi, CommitOperationAdd, hf_hub_download

REPO = os.environ.get("CURATED_REPO", "danielrosehill/HF-Model-Tags-Curated")
SEMANTIC = ("freeform", "pipeline_tag", "library", "license", "language", "region", "other", "deploy", "bucket")
OPS = {"delete", "restore"}
api = HfApi(token=os.environ.get("HF_TOKEN"))
lock = threading.Lock()
app = FastAPI()


def fetch(path: str) -> str:
    return hf_hub_download(REPO, path, repo_type="dataset", token=api.token, force_download=True)


BASE = fetch("base/tag_groups.parquet")
log = [json.loads(l) for l in Path(fetch("edits/edits.jsonl")).read_text().splitlines() if l.strip()]


def deleted() -> set[str]:
    state = {}
    for e in log:
        state[e["tag"]] = e["op"]
    return {t for t, op in state.items() if op == "delete"}


rows = duckdb.sql(f"""
  SELECT tag, kind, model_count, downloads_30d, coalesce(top_pipeline_tag, ''), n_variants, merge,
         [v.tag || '\t' || v.model_count FOR v IN variants][1:12]
  FROM '{BASE}' WHERE kind IN {SEMANTIC} ORDER BY model_count DESC""").fetchall()
kinds = sorted({r[1] for r in rows})
pipes = sorted({r[4] for r in rows})
merges = ["none", "fold", "official", "stem"]
payload = json.dumps({
    "repo": REPO, "kinds": kinds, "pipelines": pipes, "merges": merges,
    "rows": [[r[0], kinds.index(r[1]), r[2], r[3], pipes.index(r[4]), r[5], merges.index(r[6]), *(r[7] if r[5] > 1 else [])]
             for r in rows]}, separators=(",", ":"), ensure_ascii=False)


@app.get("/")
def index():
    return FileResponse(Path(__file__).parent / "index.html")


@app.get("/api/rows")
def get_rows():
    return Response(payload[:-1] + f',"deleted":{json.dumps(sorted(deleted()), ensure_ascii=False)},"edits":{len(log)}}}',
                    media_type="application/json")


@app.post("/api/save")
def save(body: dict):
    ops = body.get("ops") or []
    if not ops or any(o.get("op") not in OPS or not isinstance(o.get("tag"), str) for o in ops):
        raise HTTPException(400, "ops: [{op: delete|restore, tag: str}, ...]")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with lock:
        new = log + [{"op": o["op"], "tag": o["tag"], "at": now} for o in ops]
        state = {}
        for e in new:
            state[e["tag"]] = e["op"]
        gone = sorted(t for t, op in state.items() if op == "delete")
        with tempfile.TemporaryDirectory() as d:
            el, cur = Path(d) / "edits.jsonl", Path(d) / "tag_groups.parquet"
            el.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in new))
            c = duckdb.connect()
            c.execute("CREATE TABLE gone (tag VARCHAR)")
            c.executemany("INSERT INTO gone VALUES (?)", [(t,) for t in gone])
            c.execute(f"COPY (SELECT * FROM '{BASE}' WHERE tag NOT IN (SELECT tag FROM gone) ORDER BY model_count DESC) "
                      f"TO '{cur}' (FORMAT parquet)")
            n = sum(1 for o in ops if o["op"] == "delete")
            info = api.create_commit(REPO, repo_type="dataset", operations=[
                CommitOperationAdd("edits/edits.jsonl", str(el)), CommitOperationAdd("data/tag_groups.parquet", str(cur))],
                commit_message=f"Editor: {n} deleted, {len(ops) - n} restored ({len(gone)} deleted in total)")
        log[:] = new
    return {"saved": len(ops), "deleted_total": len(gone), "edits": len(log), "commit": info.oid}
