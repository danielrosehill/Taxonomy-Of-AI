"""Taxonomy of AI review Space: go through a task's models one by one, record a spoken note or mark reviewed.

GET  /                      the page (index.html)
GET  /api/tasks             tasks with a queue in the working dataset
GET  /api/models?task=      models of the task (live Hub stats merged over the queue) + subcategories + reviews
GET  /api/card?model=       model card markdown (front matter stripped, truncated)
POST /api/review            JSON {model_id, task}: null review ("looked at it, nothing to say")
POST /api/note              multipart {model_id, task, audio}: store audio, transcribe + structure (OpenRouter), store

Storage: private dataset VOICE_NOTES_DATASET (default danielrosehill/Taxonomy-Of-AI-Voice-Notes)
  reviews/<session file>.jsonl     one record per action, append-only; the latest record per (task, model_id) wins
  audio/<YYYY-MM-DD>/<id>.webm     the recording as the browser sent it
  transcripts/<YYYY-MM-DD>/<id>.md raw transcript with front matter
Uploaded by a CommitScheduler (every minute; a note triggers an immediate push).

Env/secrets: HF_TOKEN (read working dataset, write voice-notes dataset), OPENROUTER_API_KEY,
  NOTE_MODEL (default ~google/gemini-flash-latest), WORKING_DATASET, VOICE_NOTES_DATASET, ANNOTATOR.
"""
import base64, json, os, re, subprocess, tempfile, threading, uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from huggingface_hub import CommitScheduler, HfApi, hf_hub_download, snapshot_download

TOKEN = os.environ["HF_TOKEN"]
OR_KEY = os.environ.get("OPENROUTER_API_KEY", "")
NOTE_MODEL = os.environ.get("NOTE_MODEL", "~google/gemini-flash-latest")
WORKING = os.environ.get("WORKING_DATASET", "danielrosehill/Taxonomy-Of-AI-Working")
NOTES = os.environ.get("VOICE_NOTES_DATASET", "danielrosehill/Taxonomy-Of-AI-Voice-Notes")
ANNOTATOR = os.environ.get("ANNOTATOR", "danielrosehill")
CARD_CHARS = 12000
api = HfApi(token=TOKEN)
lock = threading.Lock()
app = FastAPI()
read_jl = lambda p: [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]
now = lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")

work = Path(snapshot_download(WORKING, repo_type="dataset", token=TOKEN, allow_patterns=["queue/*", "taxonomy/*"]))
TASKS = sorted(p.stem for p in (work / "queue").glob("*.jsonl"))

# Earlier reviews: everything already pushed, then this session's file on top.
reviews: dict[tuple[str, str], dict] = {}
api.create_repo(NOTES, repo_type="dataset", private=True, exist_ok=True)
prev = Path(snapshot_download(NOTES, repo_type="dataset", token=TOKEN, allow_patterns=["reviews/*.jsonl"]))
for p in sorted((prev / "reviews").glob("*.jsonl")) if (prev / "reviews").exists() else []:
    for r in read_jl(p):
        reviews[(r["task"], r["model_id"])] = r

upload = Path.home() / "upload"; (upload / "reviews").mkdir(parents=True, exist_ok=True)
session_file = upload / "reviews" / f"{datetime.now(timezone.utc):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:6]}.jsonl"
scheduler = CommitScheduler(repo_id=NOTES, repo_type="dataset", folder_path=upload, every=1, token=TOKEN, private=True)

_models: dict[str, dict] = {}


def task_data(task: str) -> dict:
    """Queue (snapshot) rows, with live downloads/likes/trending from the Hub merged on top; cached per task."""
    if task in _models:
        return _models[task]
    if task not in TASKS:
        raise HTTPException(404, f"no queue for {task}")
    rows = {q["model_id"]: q for q in read_jl(work / "queue" / f"{task}.jsonl")}
    live_ok = True
    try:
        for m in api.list_models(pipeline_tag=task, expand=["downloads", "downloadsAllTime", "likes", "trendingScore",
                                                             "createdAt", "tags", "library_name"]):
            q = rows.setdefault(m.id, {"model_id": m.id, "task": task, "suggested": [], "license": None, "new": True,
                                       "tags": [t for t in (m.tags or []) if ":" not in t], "library_name": m.library_name,
                                       "created_at": m.created_at.isoformat() if m.created_at else None})
            q.update(downloads_30d=m.downloads or 0, downloads_all_time=m.downloads_all_time or 0,
                     likes=m.likes or 0, trending_score=m.trending_score or 0, live=True)
    except Exception as e:  # Hub down: fall back to the snapshot numbers
        live_ok = f"{type(e).__name__}: {e}"[:200]
    tax = json.loads((work / "taxonomy" / f"{task}.json").read_text())
    cats = [{"id": s["id"], "name": s["name"]} for s in tax["subcategories"]]
    _models[task] = {"task": task, "live": live_ok, "loaded_at": now(), "subcategories": cats, "models": list(rows.values())}
    return _models[task]


def append(rec: dict):
    with lock, scheduler.lock:
        with session_file.open("a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        reviews[(rec["task"], rec["model_id"])] = rec


PROMPT = """You get a short voice note recorded while reviewing one Hugging Face model.
Model: {model_id} (pipeline_tag {task}). Hub tags: {tags}.
The reviewer's subcategories for this task (id: name): {cats}

Return one JSON object with exactly these keys:
- "transcript": verbatim transcript of the note. Fix only obvious ASR spellings of model, company and technical names.
- "summary": one sentence, the reviewer's point in their own framing.
- "verdict": "interesting" | "not-interesting" | "neutral", as the reviewer judged it.
- "reasons": list of short phrases: why it is (or is not) interesting.
- "subcategory": the subcategory id the reviewer places the model in, "new:<kebab-id>" if they name one not in the
  list, or null if they don't place it. Don't guess from the model; only from what they say.
- "secondary": list of other subcategory ids they say also fit.
- "use_cases": list of uses they mention.
- "mentioned_models": list of other models, people or projects they mention, as said.
- "follow_up": anything they say they want to do (try it, compare, revisit), or null.
Leave a list empty and a field null when the note doesn't say. Never invent content."""


def to_mp3(raw: bytes) -> bytes:
    with tempfile.TemporaryDirectory() as d:
        src, dst = Path(d) / "in", Path(d) / "out.mp3"
        src.write_bytes(raw)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(src), "-ac", "1", "-ar", "16000", "-b:a", "48k",
                        str(dst)], check=True, timeout=120)
        return dst.read_bytes()


def transcribe(mp3: bytes, model_id: str, task: str, tags: list, cats: list) -> tuple[dict, dict]:
    if not OR_KEY:
        raise HTTPException(500, "OPENROUTER_API_KEY secret missing")
    prompt = PROMPT.format(model_id=model_id, task=task, tags=", ".join(tags[:30]) or "none",
                           cats="; ".join(f"{c['id']}: {c['name']}" for c in cats))
    body = {"model": NOTE_MODEL, "response_format": {"type": "json_object"}, "usage": {"include": True},
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "input_audio", "input_audio": {"data": base64.b64encode(mp3).decode(), "format": "mp3"}}]}]}
    r = httpx.post("https://openrouter.ai/api/v1/chat/completions", json=body, timeout=180,
                   headers={"Authorization": f"Bearer {OR_KEY}"})
    if r.status_code != 200:
        raise HTTPException(502, f"OpenRouter {r.status_code}: {r.text[:300]}")
    j = r.json()
    text = j["choices"][0]["message"]["content"] or ""
    m = re.search(r"\{.*\}", text, re.S)
    try:
        out = json.loads(m.group(0) if m else text)
    except json.JSONDecodeError:
        out = {"transcript": text, "parse_error": True}
    return out, {"model": j.get("model", NOTE_MODEL), "cost": (j.get("usage") or {}).get("cost")}


@app.get("/")
def index():
    return FileResponse(Path(__file__).parent / "index.html")


@app.get("/api/tasks")
def tasks():
    return {"tasks": TASKS}


@app.get("/api/models")
def models(task: str):
    d = task_data(task)
    return {**d, "reviews": {mid: r for (t, mid), r in reviews.items() if t == task}}


@app.get("/api/card")
def card(model: str):
    try:
        t = Path(hf_hub_download(model, "README.md", token=TOKEN)).read_text(errors="replace")
    except Exception as e:
        return {"markdown": f"*(no model card: {type(e).__name__})*"}
    t = re.sub(r"\A---\n.*?\n---\n", "", t, flags=re.S).strip()
    return {"markdown": (t[:CARD_CHARS] + ("\n\n*(card truncated)*" if len(t) > CARD_CHARS else "")) or "*(empty card)*"}


@app.post("/api/review")
def review(body: dict):
    if not body.get("model_id") or not body.get("task"):
        raise HTTPException(400, "model_id and task required")
    rec = {"id": f"{datetime.now(timezone.utc):%Y-%m-%dT%H%M%S}_{uuid.uuid4().hex[:6]}", "model_id": body["model_id"],
           "task": body["task"], "status": "reviewed", "reviewed_at": now(), "annotator": ANNOTATOR,
           "audio": None, "transcript": None, "note": None, "asr": None}
    append(rec)
    return rec


@app.post("/api/note")
def note(model_id: str = Form(...), task: str = Form(...), audio: UploadFile = File(...)):
    raw = audio.file.read()
    if len(raw) < 1000:
        raise HTTPException(400, "recording empty")
    d = task_data(task)
    q = next((m for m in d["models"] if m["model_id"] == model_id), {})
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    slug = re.sub(r"[^a-z0-9]+", "-", model_id.lower()).strip("-")[:50]
    nid = f"{day}_{slug}_{uuid.uuid4().hex[:4]}"
    ext = ".ogg" if "ogg" in (audio.content_type or "") else ".mp4" if "mp4" in (audio.content_type or "") else ".webm"
    audio_rel, tr_rel = f"audio/{day}/{nid}{ext}", f"transcripts/{day}/{nid}.md"
    with lock, scheduler.lock:  # keep the original even if transcription fails
        (upload / audio_rel).parent.mkdir(parents=True, exist_ok=True)
        (upload / audio_rel).write_bytes(raw)
    try:
        out, meta = transcribe(to_mp3(raw), model_id, task, q.get("tags", []), d["subcategories"])
        status = "noted"
    except Exception as e:
        out, meta, status = {"error": str(getattr(e, "detail", e))[:300]}, {"model": NOTE_MODEL, "cost": None}, "note-failed"
    transcript = out.pop("transcript", None)
    with lock, scheduler.lock:
        (upload / tr_rel).parent.mkdir(parents=True, exist_ok=True)
        (upload / tr_rel).write_text(f"---\nid: {nid}\nmodel_id: {model_id}\ntask: {task}\nrecorded: {now()}\n"
                                     f"asr: {meta['model']}\n---\n\n{(transcript or '').strip()}\n")
    rec = {"id": nid, "model_id": model_id, "task": task, "status": status, "reviewed_at": now(), "annotator": ANNOTATOR,
           "audio": audio_rel, "transcript": transcript, "note": out, "asr": meta}
    append(rec)
    scheduler.trigger()
    return rec
