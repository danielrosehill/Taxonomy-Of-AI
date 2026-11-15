---
name: a2a-taxonomy
description: Add or refine a subcategory in this repo's unofficial audio-to-audio taxonomy, from a name and example models the user gives. Use when the user names a use case ("voice conversion", "speech enhancement", "stem separation", ...) with example HF models, or says "add a subcategory", "this is an example of X", "move X under Y".
---

# a2a-taxonomy

Records the user's subcategories of the Hugging Face `audio-to-audio` task, with example models, in `taxonomy/taxonomy.json`. The user supplies the categories and examples; you look the models up, write them down faithfully, and point out where the snapshot disagrees. The user decides what a category is; don't invent categories they didn't name. Proposing one in a sentence is fine.

## Files

- `taxonomy/taxonomy.json`: the source of truth. Edit this.
- `data/models.json` / `data/models.csv`: the 2026-11-15 snapshot of all 1,887 audio-to-audio models. Read only; refresh with `uv run scripts/fetch_models.py`.
- `README.md` section "Taxonomy": a table regenerated from the JSON (see step 5).

## Schema

```json
{
  "id": "voice-conversion",            // kebab-case, stable; never rename once used
  "name": "Voice conversion",
  "parent": null,                      // id of parent subcategory, or null
  "definition": "One or two sentences, in the user's framing: what goes in, what comes out, what it's for.",
  "use_cases": ["..."],                // concrete uses the user named
  "signals": ["tags: rvc, svc", "library: ..."],  // what in the metadata identifies members; fill in after looking
  "examples": [
    {
      "id": "author/model",            // exact HF repo id
      "in_snapshot": true,             // false if not in data/models.json
      "note": "why it's a good example (user's words where given)",
      "added": "YYYY-MM-DD"
    }
  ],
  "added": "YYYY-MM-DD",
  "notes": "open questions, overlaps with other subcategories"
}
```

## Steps

1. **Parse the request.** Subcategory name, definition, use cases, example models. The user dictates: model names may be approximate. Read "I read this as ..." and resolve them, don't ask.
2. **Resolve each example** against the snapshot, case-insensitive on `id`, then on the repo name alone:
   ```bash
   uv run python -c "import csv,sys; q=sys.argv[1].lower(); [print(r['id'],r['downloads_all_time'],r['library_name'],r['tags'][:120]) for r in csv.DictReader(open('data/models.csv')) if q in r['id'].lower()]" "<fragment>"
   ```
   Several hits: pick the original (most downloads, not a re-upload or quant) and mention the others. No hit: check the live Hub (`https://huggingface.co/api/models/<id>`); a model can exist under another pipeline tag. Record it with `in_snapshot: false` and say which tag it has. An empty search that should have hit is a suspect search; try spelling variants before concluding.
3. **Derive signals.** Look at the examples' tags, `library_name`, base models and card data. Write down any tag or field that would pick out other members, and count how many snapshot models match it. That number is an estimate; say so.
4. **Write** the entry into `taxonomy/taxonomy.json` (append, or merge into an existing subcategory by `id`), set `meta.updated` to today's date. Keep the file valid JSON (`uv run python -m json.tool taxonomy/taxonomy.json > /dev/null`).
5. **Regenerate the README table** between the `<!-- taxonomy:start -->` / `<!-- taxonomy:end -->` markers: one row per subcategory with name (indented under its parent), definition, example ids as HF links, and the signal-match count. Never hand-edit inside the markers.
6. **Commit and push**: `taxonomy: add <name>` or `taxonomy: <change>`.

Report back in two or three lines: what was added, any example that didn't resolve or wasn't in the snapshot, and the signal count.

## Context

The categories here change fast; everything is dated. Keep `added` dates absolute. The repo is public: don't record anything private about the user beyond what the README already says.
