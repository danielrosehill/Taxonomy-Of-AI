# /// script
# requires-python = ">=3.11"
# dependencies = ["duckdb>=1.1"]
# ///
"""Second-pass deduplication of the Hub tag inventory: tags.parquet -> tag_groups.parquet.

Usage: uv run scripts/dedup_hub_tags.py        (reads/writes hub-tags/out/, runs locally in seconds)

build_hub_tags.py already lists every distinct tag string. This groups strings that mean the same tag:

  1. fold      lowercase, drop everything but letters and digits: "Voice Conversion" = "voice_conversion".
  2. official  a freeform spelling whose fold equals an official Hub tag (pipeline_tag, library, license,
               language, region, other, ...) joins that tag: "Text Generation" -> text-generation.
               Official tags anchor their group and are never stemmed.
  3. stem      remaining all-letter freeform keys of 4+ letters lose inflection: plural -s/-es/-ies,
               then -ing/-ed (8+ letters), then a final -e after vowel-consonant: "finetune", "fine-tuned", "Finetuning" -> one
               group. Keys with digits (model names: qwen2, llama3) are not stemmed. STEM_EXCEPTIONS lists
               words where this would be wrong.

ID-like kinds (base_model:, dataset:, arxiv:, doi:, ...) are left as they are: one tag, one group.

Each group's counts are sums over its member tags, so a model tagged with two spellings of the same tag is
counted twice ("taggings", not distinct models). Distinct-model counts need the 3.2M-row source, which this
script deliberately doesn't read.
"""
import json, re
from pathlib import Path
import duckdb

OUT = Path(__file__).resolve().parent.parent / "hub-tags" / "out"
MERGEABLE = ("freeform", "pipeline_tag", "library", "license", "language", "region", "other", "deploy", "bucket")
STEM_EXCEPTIONS = {"news", "less", "physics", "mathematics", "economics", "robotics", "genomics", "proteomics",
                   "metabolomics", "analytics", "graphics", "linguistics", "statistics", "ethics", "electronics",
                   "series", "species", "lens", "gas", "bias", "chaos", "corpus", "status", "focus", "thesis",
                   "embed", "embedded", "speed", "seed", "need", "feed", "red", "bed", "bing", "king", "ring",
                   "thing", "string", "spring", "sing", "wing", "ping", "being", "wedding", "pudding"}


def fold(t: str) -> str:
    return re.sub(r"[^\w]|_", "", t.lower())


def stem(k: str) -> str:
    if not k.isalpha() or len(k) < 4 or k in STEM_EXCEPTIONS:
        return k
    if k.endswith("ies") and len(k) > 5: k = k[:-3] + "y"
    elif k.endswith(("sses", "shes", "ches", "xes")): k = k[:-2]
    elif k.endswith("s") and not k.endswith(("ss", "us", "is", "os")): k = k[:-1]
    if len(k) >= 8 and k.endswith("ing"): k = k[:-3]
    elif len(k) >= 8 and k.endswith("ed"): k = k[:-2]
    # final -e only in a vowel-consonant-e ending (tune, quantize), so olmoe/yoloe/agente keep theirs
    if len(k) >= 5 and k.endswith("e") and k[-2] not in "aeiouy" and k[-3] in "aeiouy": k = k[:-1]
    return k


c = duckdb.connect()
rows = c.sql(f"SELECT tag, kind, model_count, downloads_30d, downloads_all_time, top_pipeline_tag "
             f"FROM '{OUT}/tags.parquet'").fetchall()

official = {}  # fold key -> group id of the best official tag with that fold
for tag, kind, n, *_ in sorted(rows, key=lambda r: -r[2]):
    if kind in MERGEABLE and kind != "freeform":
        official.setdefault(fold(tag), tag)

groups = {}
for tag, kind, n, d30, dall, pipe in rows:
    if kind not in MERGEABLE:
        gid, rule = tag, "none"
    elif kind != "freeform":
        gid, rule = official[fold(tag)] if fold(tag) in official else tag, "official"
    else:
        k = fold(tag)
        if not k:
            continue
        if k in official:
            gid, rule = official[k], "official"
        else:
            s = stem(k)
            gid, rule = ("~" + s, "stem" if s != k else "fold")
    g = groups.setdefault(gid, {"members": [], "rules": set()})
    g["members"].append((tag, kind, n, d30, dall, pipe))
    g["rules"].add(rule)

out = []
for gid, g in groups.items():
    m = sorted(g["members"], key=lambda r: -r[2])
    anchor = next((r for r in m if r[1] != "freeform"), m[0])  # official tag names the group if there is one
    rules = g["rules"]
    out.append({
        "tag": anchor[0], "kind": anchor[1],
        "model_count": sum(r[2] for r in m), "downloads_30d": sum(r[3] for r in m),
        "downloads_all_time": sum(r[4] for r in m), "top_pipeline_tag": m[0][5],
        "n_variants": len(m),
        "merge": ("none" if len(m) == 1 else "official" if "official" in rules
                  else "stem" if len({fold(r[0]) for r in m}) > 1 else "fold"),
        "variants": [{"tag": r[0], "kind": r[1], "model_count": r[2]} for r in m],
    })

tmp = OUT / "tag_groups.json"
tmp.write_text(json.dumps(out))
c.sql(f"""COPY (SELECT * FROM read_json('{tmp}', columns={{tag:'VARCHAR', kind:'VARCHAR', model_count:'BIGINT',
  downloads_30d:'BIGINT', downloads_all_time:'BIGINT', top_pipeline_tag:'VARCHAR', n_variants:'BIGINT', merge:'VARCHAR',
  variants:'STRUCT(tag VARCHAR, kind VARCHAR, model_count BIGINT)[]'}}, maximum_object_size=1000000000)
  ORDER BY model_count DESC) TO '{OUT}/tag_groups.parquet' (FORMAT parquet)""")
tmp.unlink()

summary = json.loads((OUT / "summary.json").read_text())
summary["dedup"] = {
    "distinct_tags": len(rows), "groups": len(out),
    "merged_groups": sum(1 for g in out if g["n_variants"] > 1),
    "by_merge": {k: sum(1 for g in out if g["merge"] == k) for k in ("none", "fold", "official", "stem")},
    "freeform_groups": sum(1 for g in out if g["kind"] == "freeform"),
}
(OUT / "summary.json").write_text(json.dumps(summary, indent=2))
print(json.dumps(summary["dedup"], indent=2))
