"""Annotation Space for Taxonomy-Of-AI.

Shows one model at a time from queue/<task>.jsonl in the private working dataset, with its card,
and records a subcategory label per click to annotations/ in the same dataset (CommitScheduler, every minute).
Categories are the buttons from taxonomy/<task>.json; restart the Space after syncing new ones.
Env: HF_TOKEN (write access to the working dataset), WORKING_DATASET, TASK.
"""
import json, os, re, uuid
from datetime import datetime, timezone
from pathlib import Path

import gradio as gr
from huggingface_hub import CommitScheduler, hf_hub_download, snapshot_download

TOKEN = os.environ["HF_TOKEN"]
WORKING = os.environ.get("WORKING_DATASET", "danielrosehill/Taxonomy-Of-AI-Working")
TASK = os.environ.get("TASK", "audio-to-audio")
ANNOTATOR = os.environ.get("ANNOTATOR", "danielrosehill")
CARD_CHARS = 8000

local = Path(snapshot_download(WORKING, repo_type="dataset", token=TOKEN,
                               allow_patterns=[f"queue/{TASK}.jsonl", f"taxonomy/{TASK}.json", "annotations/*"]))
read_jl = lambda p: [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
queue = read_jl(local / "queue" / f"{TASK}.jsonl")
taxonomy = json.loads((local / "taxonomy" / f"{TASK}.json").read_text())
CATS = [(s["id"], s["name"]) for s in taxonomy["subcategories"]]
CAT_NAME = dict(CATS)

done = {}
for p in sorted((local / "annotations").glob("*.jsonl")) if (local / "annotations").exists() else []:
    for r in read_jl(p):
        done[r["model_id"]] = r

out_dir = Path("annotations_local"); out_dir.mkdir(exist_ok=True)
out_file = out_dir / f"{datetime.now(timezone.utc):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:6]}.jsonl"
scheduler = CommitScheduler(repo_id=WORKING, repo_type="dataset", folder_path=out_dir,
                            path_in_repo="annotations", every=1, token=TOKEN, private=True)


def card_text(model_id):
    try:
        p = hf_hub_download(model_id, "README.md", token=TOKEN)
        t = Path(p).read_text(errors="replace")
        t = re.sub(r"\A---\n.*?\n---\n", "", t, flags=re.S)
        return t[:CARD_CHARS] + ("\n\n*(card truncated)*" if len(t) > CARD_CHARS else "") or "*(empty card)*"
    except Exception as e:
        return f"*(no model card: {type(e).__name__})*"


def next_index(start, only_unlabelled=True):
    for i in range(start, len(queue)):
        if not only_unlabelled or queue[i]["model_id"] not in done:
            return i
    return None


def view(i):
    n = sum(1 for q in queue if q["model_id"] in done)
    prog = f"**{n} / {len(queue)} labelled** ({TASK})"
    if i is None:
        return i, prog, "## Queue finished", "", "", gr.update(value=[]), ""
    q = queue[i]
    mid = q["model_id"]
    head = (f"## [{mid}](https://huggingface.co/{mid})\n"
            f"#{i + 1} · downloads (all time) {q['downloads_all_time']:,} · likes {q['likes']} · "
            f"created {(q['created_at'] or '')[:10]} · library `{q['library_name']}` · license `{q['license']}`")
    sug = ", ".join(CAT_NAME.get(s, s) for s in q["suggested"]) or "none"
    prev = done.get(mid)
    meta = f"**Tag-signal suggestion:** {sug}\n\n**Tags:** {', '.join(q['tags'][:30])}"
    if prev:
        meta += f"\n\n**Already labelled:** `{prev['subcategory']}` ({prev['labeled_at'][:10]})"
    return i, prog, head, meta, card_text(mid), gr.update(value=[]), ""


def record(i, subcategory, secondary, notes):
    if i is None:
        return view(None)
    q = queue[i]
    rec = {"model_id": q["model_id"], "task": TASK, "subcategory": subcategory,
           "secondary": [s for s in (secondary or []) if s != subcategory], "source": "annotation",
           "annotator": ANNOTATOR, "labeled_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "notes": (notes or "").strip()}
    with scheduler.lock:
        with out_file.open("a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    done[q["model_id"]] = rec
    return view(next_index(i + 1))


with gr.Blocks(title="Taxonomy of AI: annotate") as demo:
    idx = gr.State(None)
    progress = gr.Markdown()
    header = gr.Markdown()
    with gr.Row():
        cat_buttons = [gr.Button(name, variant="primary") for _, name in CATS]
    secondary = gr.CheckboxGroup(choices=[(n, c) for c, n in CATS], label="Also fits (optional, tick before clicking a category)")
    notes = gr.Textbox(label="Notes (optional, saved with the label)", lines=1)
    with gr.Row():
        new_cat = gr.Textbox(label="New category (kebab-case id)", scale=3)
        new_btn = gr.Button("Label as new category", scale=1)
    with gr.Row():
        unsure = gr.Button("Unsure")
        other = gr.Button("Not a use case I track / misc")
        bad = gr.Button("Not really audio-to-audio")
        skip = gr.Button("Skip (no label)")
    with gr.Row():
        jump = gr.Number(label="Jump to # (1-based)", precision=0, scale=1)
        jump_btn = gr.Button("Go", scale=1)
    meta = gr.Markdown()
    card = gr.Markdown(label="Model card")

    outs = [idx, progress, header, meta, card, secondary, notes]
    for (cid, _), b in zip(CATS, cat_buttons):
        b.click(lambda i, s, n, cid=cid: record(i, cid, s, n), [idx, secondary, notes], outs)
    new_btn.click(lambda i, s, n, c: record(i, "new:" + re.sub(r"[^a-z0-9-]+", "-", (c or "unnamed").lower()).strip("-"), s, n),
                  [idx, secondary, notes, new_cat], outs)
    unsure.click(lambda i, s, n: record(i, "_unsure", s, n), [idx, secondary, notes], outs)
    other.click(lambda i, s, n: record(i, "_other", s, n), [idx, secondary, notes], outs)
    bad.click(lambda i, s, n: record(i, "_not-task", s, n), [idx, secondary, notes], outs)
    skip.click(lambda i: view(next_index((i or 0) + 1)), [idx], outs)
    jump_btn.click(lambda j: view(min(max(int(j or 1), 1), len(queue)) - 1), [jump], outs)
    demo.load(lambda: view(next_index(0)), None, outs)

demo.launch()
