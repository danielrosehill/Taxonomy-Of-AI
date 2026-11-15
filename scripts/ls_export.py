#!/usr/bin/env python3
"""Export Taxonomy-of-AI labels from Carrot Cake Lab (Label Studio) to the working dataset.

Writes the record format of the space/ annotator (space/app.py `record`), so the sync and analysis code reads
Label Studio labels and Space labels alike:
    {model_id, task, subcategory, secondary[], source: "annotation", annotator, labeled_at, notes}
one JSON line per labelled model, in one file `annotations/<UTCts>-ls<project>.jsonl` per export, committed to the
private dataset danielrosehill/Taxonomy-Of-AI-Working (path the Space's CommitScheduler used).

Label Studio project: 34 "Taxonomy of AI: audio-to-audio" (https://carrotcakelab.com/projects/34); API on the LAN
http://10.0.0.2:8140 (the public hostname is behind Cloudflare Access). Controls: Choices `subcategory` (category id,
or `_new` + TextArea `new_category`, `_unsure`, `_other`, `_not-task`), Choices `secondary` (multiple), TextArea `notes`.

    with-secrets uv run scripts/ls_export.py --project 34 --out /tmp/toa-export          # write locally
    with-secrets uv run scripts/ls_export.py --project 34 --out /tmp/toa-export --push   # + one commit

Rules: latest non-cancelled annotation per task; skipped tasks are not written (the Space's Skip wrote nothing);
`_new` becomes `new:<kebab id>` exactly as the Space did; the subcategory is removed from `secondary`;
models already in the dataset's annotations/ are re-exported only with --include-existing.
"""
# /// script
# dependencies = ["huggingface_hub", "requests"]
# ///
import argparse, json, os, re, sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from huggingface_hub import HfApi, snapshot_download

WORKING = "danielrosehill/Taxonomy-Of-AI-Working"
LS_URL = os.environ.get("CCL_API_URL", "http://10.0.0.2:8140")
ANNOTATORS = {1: "danielrosehill", 2: "HannahRSR"}  # HF usernames, as the Space's ANNOTATOR default


def ls_export(project: int) -> list[dict]:
    r = requests.get(f"{LS_URL}/api/projects/{project}/export", params={"exportType": "JSON"},
                     headers={"Authorization": f"Token {os.environ['LABEL_STUDIO_ADMIN_TOKEN']}"}, timeout=300)
    r.raise_for_status()
    return r.json()


def record(task: dict, ann: dict, warn) -> dict | None:
    d = task["data"]
    got = {}
    for r in ann["result"]:
        v = r.get("value", {})
        got[r["from_name"]] = v.get("choices") if "choices" in v else (v.get("text") or [""])
    sub = (got.get("subcategory") or [None])[0]
    if sub is None:
        warn(f"{d['model_id']}: no subcategory, skipped")
        return None
    if sub == "_new":
        raw = " ".join(got.get("new_category") or []).strip()
        if not raw:
            warn(f"{d['model_id']}: New category without an id; written as new:unnamed")
        sub = "new:" + re.sub(r"[^a-z0-9-]+", "-", (raw or "unnamed").lower()).strip("-")
    when = datetime.fromisoformat(ann["updated_at"].replace("Z", "+00:00")).astimezone(timezone.utc)
    return {"model_id": d["model_id"], "task": d["task"], "subcategory": sub,
            "secondary": [s for s in (got.get("secondary") or []) if s != sub], "source": "annotation",
            "annotator": ANNOTATORS.get(ann["completed_by"], f"ls-user-{ann['completed_by']}"),
            "labeled_at": when.isoformat(timespec="seconds"),
            "notes": " ".join(got.get("notes") or []).strip()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", type=int, default=34); ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--push", action="store_true"); ap.add_argument("--include-existing", action="store_true")
    a = ap.parse_args()
    warn = lambda m: print("WARN", m, file=sys.stderr)
    existing = set()
    if not a.include_existing:
        local = Path(snapshot_download(WORKING, repo_type="dataset", token=os.environ["HF_TOKEN"], allow_patterns=["annotations/*"]))
        for p in (local / "annotations").glob("*.jsonl") if (local / "annotations").exists() else []:
            existing |= {json.loads(l)["model_id"] for l in p.read_text().splitlines() if l.strip()}
    recs = []
    for t in ls_export(a.project):
        anns = [x for x in t.get("annotations", []) if not x.get("was_cancelled")]
        if not anns or t["data"]["model_id"] in existing:
            continue
        r = record(t, max(anns, key=lambda x: x["updated_at"]), warn)
        if r:
            recs.append(r)
    name = f"{datetime.now(timezone.utc):%Y%m%dT%H%M%S}-ls{a.project}.jsonl"
    (a.out / "annotations").mkdir(parents=True, exist_ok=True)
    path = a.out / "annotations" / name
    if recs:
        path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in recs), encoding="utf-8")
    print(json.dumps({"records": len(recs), "file": str(path) if recs else None, "skipped_existing": len(existing)}))
    if a.push and recs:
        c = HfApi(token=os.environ["HF_TOKEN"]).upload_file(
            path_or_fileobj=str(path), path_in_repo=f"annotations/{name}", repo_id=WORKING, repo_type="dataset",
            commit_message=f"label-studio export Taxonomy of AI {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
        print(json.dumps({"pushed": name, "commit": str(c)}))


if __name__ == "__main__":
    main()
