---
name: notes-to-taxonomy
description: Turn the user's freeform notes or a voice recording about a Hugging Face task (dictated rambles, pasted lists of model links with comments, half-sorted thoughts) into subcategory entries in tasks/<task>/taxonomy.json. Use when the user pastes or dictates notes on models or use cases, gives an audio file or voice note, or says "here are my notes on <task>", "sort these into the taxonomy", "turn this into categories".
---

# notes-to-taxonomy

Front end to the `task-taxonomy` skill (`.claude/skills/task-taxonomy/SKILL.md`): that skill writes one subcategory
from a clean request; this one gets there from messy input, which can hold several subcategories, examples
for existing ones, moves, and asides. Read `task-taxonomy` first: its schema, files and steps 2-7 apply unchanged.

## 1. Get text

- **Typed or pasted notes:** use as is.
- **Audio** (path, URL, or "the voice note I just sent"): transcribe with whatever transcription skill or ASR
  endpoint the session has. Prefer one that handles technical vocabulary; model IDs come out mangled either way
  ("parakeet tee dee tee" = `parakeet-tdt`), and step 3 fixes them. Keep the transcript in your reply, not in the repo.
- Dictated text has no punctuation and runs ideas together. Say "I read this as ..." where it matters; don't
  call the wording garbled and don't ask the user to repeat it.

## 2. Pick the task

From what the notes say, or the models' `pipeline_tag`. The default is the task the user was last working on
(`audio-to-audio` until another exists). A new task: follow "New task" in `task-taxonomy`.

## 3. Pull the notes apart

Read `tasks/<task>/taxonomy.json` first, so you know what exists. Then sort every statement in the notes into one of:

| Kind | Example in the notes | Becomes |
|---|---|---|
| new subcategory | "then there's a whole bunch that do X" | new entry (name, definition, use cases) |
| example | a model link or name, plus why it fits | `examples[]` item, `note` in the user's words |
| assignment to an existing subcategory | "this one is really another voice changer" | example on that entry |
| hierarchy | "X is a kind of Y", "under Z" | `parent` |
| boundary / overlap | "the line between A and B is ..." | `notes` on both entries, or `definition` |
| use case | "I use these for cleaning TTS training data" | `use_cases[]` |
| aside | anything about the user, other projects, opinions | nothing; leave it out |

Rules:
- The user names the categories. A cluster of models with no category name: propose one, say so, and mark
  it in `notes` as proposed. Don't split or merge the user's categories without saying so.
- Match against existing ids before adding; "voice changers" probably is `voice-conversion`. Never rename an
  existing `id`.
- Keep the user's framing and words in `definition` and `note`, tightened, not paraphrased into generic copy.
  Drop anything personal: the repo and dataset are public.
- Resolve every model as in `task-taxonomy` step 2 (snapshot, then live Hub API, spelling variants). For a
  mangled or partial name, search: `https://huggingface.co/api/models?search=<word>&limit=10`.

## 4. Show the plan, then write

Before editing, show a short table: subcategory (new / existing), parent, examples with resolved ids, and anything
unresolved or guessed. One line per row. If nothing is ambiguous, carry on in the same turn; ask only about a
model you couldn't resolve or a category you can't place.

Then run `task-taxonomy` steps 3-7 for each touched entry (signals, write JSON, regenerate README table, sync the
Hub datasets, restart nothing unless the Space is in use, commit and push) in **one** commit:
`taxonomy(<task>): notes of YYYY-MM-DD: <n> new, <m> updated`.

## 5. Report

Two or three lines: what was added and updated, what didn't resolve, and any proposed category the user should
confirm. Tag evidence for a new category: check the explorer data (`hub-tags/out/tag_groups.parquet`, or
<https://huggingface.co/spaces/danielrosehill/HF-Tag-Explorer>) for freeform tags authors already use for it.
