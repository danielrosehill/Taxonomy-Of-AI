---
name: task-taxonomy
description: Add or refine a subcategory in this repo's taxonomy of a Hugging Face task (audio-to-audio first, others later), from a name and example models the user gives; also start a new task. Use when the user names a use case ("voice conversion", "stem separation", ...) with example HF models, or says "add a subcategory", "this is an example of X", "move X under Y", "start on <pipeline_tag>".
---

# task-taxonomy

Records the user's subcategories of a Hugging Face `pipeline_tag` task, with example models, in `tasks/<task>/taxonomy.json`. The user supplies the categories and examples; you look the models up, write them down faithfully, and point out where the snapshot disagrees. The user decides what a category is; don't invent categories they didn't name. Proposing one in a sentence is fine.

## Files (per task)

- `tasks/<task>/taxonomy.json`: the source of truth. Edit this.
- `tasks/<task>/data/models.json` / `models.csv`: Hub snapshot for the task. Read only; refresh with `uv run scripts/fetch_task_models.py <task>`.
- `tasks/<task>/README.md`: the taxonomy table between `<!-- taxonomy:start -->` / `<!-- taxonomy:end -->`, regenerated from the JSON (step 5).
- Hub datasets `danielrosehill/Taxonomy-Of-AI` (public) and `-Working` (private): updated by `uv run scripts/sync_hf_datasets.py <task>` (step 6).

**New task:** run the fetch script, create `tasks/<task>/taxonomy.json` with `{"meta": {"task", "snapshot", "started", "updated"}, "subcategories": []}`, copy the README structure from `tasks/audio-to-audio/README.md`, and add a row to the Tasks table in the root `README.md`.

## Schema (one subcategory)

```json
{
  "id": "voice-conversion",            // kebab-case, stable; never rename once used (labels reference it)
  "name": "Voice conversion",
  "parent": null,                      // id of parent subcategory, or null
  "definition": "One or two sentences, in the user's framing: what goes in, what comes out, what it's for.",
  "use_cases": ["..."],                // concrete uses the user named
  "signals": ["tags: rvc, svc"],       // human-readable description of the signal
  "signal_tags": ["rvc", "svc"],       // exact tags, matched case-insensitively; drives Space suggestions
  "signal_count": 399,                 // snapshot models with at least one signal tag
  "examples": [
    {"id": "author/model", "in_snapshot": true, "note": "why it's a good example (user's words where given)", "added": "YYYY-MM-DD"}
  ],
  "added": "YYYY-MM-DD",
  "notes": "open questions, overlaps with other subcategories"
}
```

## Steps

1. **Parse the request.** Subcategory name, definition, use cases, example models. The user dictates: names may be approximate. Say "I read this as ..." and resolve them; don't ask.
2. **Resolve each example** against `tasks/<task>/data/models.json`, case-insensitive on `id`, then on the repo name alone. Several hits: pick the original (most downloads, not a re-upload or quant) and mention the others. No hit: check the live Hub (`https://huggingface.co/api/models/<id>`); a model can sit under another pipeline tag. Record it with `in_snapshot: false` and say which tag it has. An empty search that should have hit is a suspect search; try spelling variants before concluding.
3. **Derive signals.** Look at the examples' tags, `library_name`, base models and card data. Authors' freeform tags are often the best signal (see "Freeform tags as evidence" in the root README); also check spelling and case variants (`RVC`, `rvc`, `Voice Conversion`). Count the snapshot models matching any signal tag. It's an estimate; say so.
4. **Write** the entry into `tasks/<task>/taxonomy.json` (append, or merge by `id`); set `meta.updated` to today. Validate: `python3 -m json.tool tasks/<task>/taxonomy.json > /dev/null`.
5. **Regenerate the task README table** inside the markers: name (indented under its parent), definition, example ids as HF links, `signal_count`. Never hand-edit inside the markers. Update the subcategory count in the root README's Tasks table.
6. **Sync the Hub datasets:** `uv run scripts/sync_hf_datasets.py <task>`. The annotation Space reads categories at startup, so restart it afterwards: `hf spaces restart danielrosehill/Taxonomy-Of-AI-Annotator` (or HfApi().restart_space).
7. **Commit and push**: `taxonomy(<task>): add <name>`.

Report back in two or three lines: what was added, any example that didn't resolve or wasn't in the snapshot, and the signal count.

## Context

Categories in this space change fast; everything is dated. Keep dates absolute. The repo and the public dataset are public: record nothing private about the user beyond what the README already says.
