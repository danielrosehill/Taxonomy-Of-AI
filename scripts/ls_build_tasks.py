#!/usr/bin/env python3
"""Build Label Studio tasks for Carrot Cake Lab from the Taxonomy-Of-AI working queue.

Replaces the unpublished Gradio annotator in space/ (same queue, same order, same labels). Reads
`queue/<task>.jsonl` from the private dataset danielrosehill/Taxonomy-Of-AI-Working (most-downloaded first, built by
sync_hf_datasets.py), skips models already labelled in `annotations/`, fetches each model card (first 8,000 chars, as
the Space did) and writes tasks JSON. The tag-signal `suggested` subcategories become a prediction
(model_version "tag-signal": first suggestion = subcategory, the rest = secondary).

    with-secrets uv run scripts/ls_build_tasks.py audio-to-audio --start 0 --n 15 -o /tmp/toa/tasks.json
    with-secrets python3 -I <ccl.py> import <pid> /tmp/toa/tasks.json [--confirm]
"""
# /// script
# dependencies = ["huggingface_hub", "markdown"]
# ///
import argparse, html, json, os, re
from pathlib import Path

import markdown
from huggingface_hub import hf_hub_download, snapshot_download

WORKING = "danielrosehill/Taxonomy-Of-AI-Working"
CARD_CHARS = 8000


def card_html(model_id: str, token: str) -> str:
    try:
        t = Path(hf_hub_download(model_id, "README.md", token=token)).read_text(errors="replace")
    except Exception as e:
        return f"<p><i>(no model card: {type(e).__name__})</i></p>"
    t = re.sub(r"\A---\n.*?\n---\n", "", t, flags=re.S)
    cut = len(t) > CARD_CHARS
    body = markdown.markdown(t[:CARD_CHARS], extensions=["tables", "fenced_code"]) if t.strip() else "<p><i>(empty card)</i></p>"
    body = re.sub(r"<(script|iframe|style)\b.*?</\1>", "", body, flags=re.S | re.I)
    return body + ("<p><i>(card truncated)</i></p>" if cut else "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("task"); ap.add_argument("--start", type=int, default=0); ap.add_argument("--n", type=int, default=15)
    ap.add_argument("-o", required=True)
    a = ap.parse_args()
    token = os.environ["HF_TOKEN"]
    local = Path(snapshot_download(WORKING, repo_type="dataset", token=token,
                                   allow_patterns=[f"queue/{a.task}.jsonl", f"taxonomy/{a.task}.json", "annotations/*"]))
    queue = [json.loads(l) for l in (local / "queue" / f"{a.task}.jsonl").read_text().splitlines() if l.strip()]
    names = {s["id"]: s["name"] for s in json.loads((local / "taxonomy" / f"{a.task}.json").read_text())["subcategories"]}
    done = set()
    for p in (local / "annotations").glob("*.jsonl") if (local / "annotations").exists() else []:
        done |= {json.loads(l)["model_id"] for l in p.read_text().splitlines() if l.strip()}
    todo = [(i, q) for i, q in enumerate(queue) if q["model_id"] not in done][a.start:a.start + a.n]
    tasks = []
    for rank, q in todo:
        mid = q["model_id"]
        sug = q["suggested"]
        head = (f'<h3><a href="https://huggingface.co/{html.escape(mid)}" target="_blank">{html.escape(mid)}</a></h3>'
                f'<p>#{rank + 1} · downloads (all time) {int(q["downloads_all_time"]):,} · likes {q["likes"]} · '
                f'created {(q["created_at"] or "")[:10]} · library <code>{html.escape(str(q["library_name"]))}</code> · '
                f'license <code>{html.escape(str(q["license"]))}</code></p>'
                f'<p><b>Tag-signal suggestion:</b> {html.escape(", ".join(names.get(s, s) for s in sug) or "none")}</p>'
                f'<p><b>Tags:</b> {html.escape(", ".join(q["tags"][:30]))}</p>')
        t = {"data": {"model_id": mid, "task": q["task"], "rank": rank + 1, "suggested": sug,
                      "header_html": head, "card_html": card_html(mid, token)}}
        if sug:
            res = [{"from_name": "subcategory", "to_name": "card", "type": "choices", "value": {"choices": [sug[0]]}}]
            if sug[1:]:
                res.append({"from_name": "secondary", "to_name": "card", "type": "choices", "value": {"choices": sug[1:]}})
            t["predictions"] = [{"model_version": "tag-signal", "score": round(1 / len(sug), 2), "result": res}]
        tasks.append(t)
    Path(a.o).write_text(json.dumps(tasks, ensure_ascii=False))
    print(json.dumps({"tasks": len(tasks), "with_prediction": sum("predictions" in t for t in tasks),
                      "already_labelled": len(done), "queue": len(queue)}))


if __name__ == "__main__":
    main()
