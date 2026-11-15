# /// script
# requires-python = ">=3.11"
# dependencies = ["huggingface_hub>=0.30"]
# ///
"""Store a voice note (and its transcript) in the private dataset danielrosehill/Taxonomy-Of-AI-Voice-Notes.

Usage:
  uv run scripts/voice_note.py init
  uv run scripts/voice_note.py add <audio> --transcript <file.txt|md> [--task audio-to-audio] [--slug short-name]
      [--asr <model id>] [--recorded YYYY-MM-DD]
  uv run scripts/voice_note.py processed <note id> <subcategory id> [...]   -> marks what the note became

Layout:
  audio/<YYYY-MM-DD>/<id>.<ext>        original recording, unchanged
  transcripts/<YYYY-MM-DD>/<id>.md     raw ASR transcript (not cleaned up)
  notes.jsonl                          one line per note: id, recorded, task, audio, transcript, asr, added,
                                       processed_into (taxonomy subcategory ids), processed_at
id = <YYYY-MM-DD>_<slug>. Transcription is done before calling this (any ASR); see the notes-to-taxonomy skill.
"""
import argparse, json, re, tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from huggingface_hub import HfApi, CommitOperationAdd, hf_hub_download

REPO = "danielrosehill/Taxonomy-Of-AI-Voice-Notes"
CARD = Path(__file__).resolve().parent.parent / "voice-notes" / "README.dataset.md"
api = HfApi()


def load() -> list[dict]:
    try:
        p = hf_hub_download(REPO, "notes.jsonl", repo_type="dataset", force_download=True)
    except Exception:
        return []
    return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]


def dump(notes: list[dict]) -> bytes:
    return "".join(json.dumps(n, ensure_ascii=False) + "\n" for n in notes).encode()


ap = argparse.ArgumentParser()
sub = ap.add_subparsers(dest="cmd", required=True)
sub.add_parser("init")
a = sub.add_parser("add"); a.add_argument("audio"); a.add_argument("--transcript", required=True)
a.add_argument("--task", default="audio-to-audio"); a.add_argument("--slug"); a.add_argument("--asr", default="")
a.add_argument("--recorded", default=date.today().isoformat())
p = sub.add_parser("processed"); p.add_argument("id"); p.add_argument("subcategories", nargs="+")
args = ap.parse_args()
now = datetime.now(timezone.utc).isoformat(timespec="seconds")

if args.cmd == "init":
    api.create_repo(REPO, repo_type="dataset", private=True, exist_ok=True)
    ops = [CommitOperationAdd("README.md", str(CARD))]
    if not api.file_exists(REPO, "notes.jsonl", repo_type="dataset"):
        ops.append(CommitOperationAdd("notes.jsonl", b""))
    api.create_commit(REPO, repo_type="dataset", operations=ops, commit_message="Init voice notes dataset")
    print(f"https://huggingface.co/datasets/{REPO}")
elif args.cmd == "add":
    audio = Path(args.audio)
    slug = re.sub(r"[^a-z0-9]+", "-", (args.slug or audio.stem).lower()).strip("-")[:60]
    nid, d = f"{args.recorded}_{slug}", args.recorded
    notes = load()
    if any(n["id"] == nid for n in notes):
        raise SystemExit(f"{nid} exists; pass another --slug")
    text = Path(args.transcript).read_text()
    md = f"---\nid: {nid}\nrecorded: {d}\ntask: {args.task}\nasr: {args.asr}\n---\n\n{text.strip()}\n"
    note = {"id": nid, "recorded": d, "task": args.task, "audio": f"audio/{d}/{nid}{audio.suffix.lower()}",
            "transcript": f"transcripts/{d}/{nid}.md", "asr": args.asr, "added": now, "processed_into": [], "processed_at": None}
    api.create_commit(REPO, repo_type="dataset", commit_message=f"Voice note {nid}", operations=[
        CommitOperationAdd(note["audio"], str(audio)), CommitOperationAdd(note["transcript"], md.encode()),
        CommitOperationAdd("notes.jsonl", dump(notes + [note]))])
    print(json.dumps(note))
else:
    notes = load()
    n = next((n for n in notes if n["id"] == args.id), None)
    if n is None:
        raise SystemExit(f"no note {args.id}")
    n["processed_into"] = sorted(set(n["processed_into"]) | set(args.subcategories)); n["processed_at"] = now
    api.create_commit(REPO, repo_type="dataset", commit_message=f"Processed {args.id}",
                      operations=[CommitOperationAdd("notes.jsonl", dump(notes))])
    print(json.dumps(n))
