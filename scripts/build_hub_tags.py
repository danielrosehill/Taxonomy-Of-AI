# /// script
# requires-python = ">=3.11"
# dependencies = ["duckdb>=1.1"]
# ///
"""Deduplicated list of every tag on every Hugging Face model, from cfahlgren1/hub-stats.

Usage: uv run scripts/build_hub_tags.py          -> hub-tags/out/*.parquet + summary.json
On Colab (skill data-notebooks:colab-run-job): OUT_DIR=/content/out, DUCKDB_MEMORY=8GB.

Reads only the id/tags/pipeline_tag/downloads columns of models.parquet over HTTP (~50 MB of the 1.7 GB file).
DuckDB memory is capped (DUCKDB_MEMORY, default 1GB) and spills to disk. Built 2026-11-15 on a Colab CPU VM.
"""
import json, os, sys, threading, time
from datetime import datetime, timezone
from pathlib import Path
import duckdb, urllib.request

SRC = "https://huggingface.co/api/datasets/cfahlgren1/hub-stats/parquet/models/train/0.parquet"
OUT = Path(os.environ.get("OUT_DIR") or Path(__file__).resolve().parent.parent / "hub-tags" / "out")
OUT.mkdir(parents=True, exist_ok=True)
c = duckdb.connect()
c.sql(f"SET memory_limit='{os.environ.get('DUCKDB_MEMORY', '1GB')}'; SET threads={os.cpu_count() or 2}; SET preserve_insertion_order=false")
c.sql(f"SET temp_directory='{OUT.parent / '.duckdb_tmp'}'")
T0 = time.time()
def _beat():  # keep output flowing so remote kernels don't time out
    while True:
        time.sleep(10); print(f'... {time.time() - T0:.0f}s', flush=True)
threading.Thread(target=_beat, daemon=True).start()
step = lambda m: print(f'[{time.time() - T0:.0f}s] {m}', flush=True)

step("reading tags"); c.sql(f"""CREATE TABLE mt AS
  SELECT DISTINCT id, unnest(tags) AS tag, pipeline_tag, coalesce(downloads,0) AS d30, coalesce(downloadsAllTime,0) AS dall
  FROM read_parquet('{SRC}')""")
# Official tag types (language, library, license, region, pipeline_tag, dataset, other, ...) from the Hub.
by_type = json.load(urllib.request.urlopen("https://huggingface.co/api/models-tags-by-type", timeout=60))
c.sql("CREATE TABLE official (tag VARCHAR, tag_type VARCHAR)")
c.executemany("INSERT INTO official VALUES (?, ?)", [(t["id"], k) for k, v in by_type.items() for t in v])
# Otherwise a prefix counts as a structured namespace ("base_model:", "arxiv:") if 50+ distinct tags use it.
c.sql("""CREATE TABLE prefixes AS
  SELECT split_part(tag, ':', 1) AS p FROM (SELECT DISTINCT tag FROM mt) WHERE tag LIKE '%:%'
  GROUP BY 1 HAVING count(*) >= 50""")
step("aggregating")
c.sql("""CREATE TABLE tags AS
  WITH per_pipe AS (SELECT tag, pipeline_tag, count(*) n FROM mt WHERE pipeline_tag IS NOT NULL GROUP BY 1,2),
       top AS (SELECT tag, arg_max(pipeline_tag, n) top_pipeline_tag, max(n) top_n FROM per_pipe GROUP BY 1),
       agg AS (SELECT tag, count(*)::BIGINT model_count, sum(d30)::BIGINT downloads_30d, sum(dall)::BIGINT downloads_all_time
               FROM mt GROUP BY 1)
  SELECT a.tag,
         coalesce(o.tag_type, CASE WHEN a.tag LIKE '%:%' AND split_part(a.tag, ':', 1) IN (SELECT p FROM prefixes)
                               THEN split_part(a.tag, ':', 1) ELSE 'freeform' END) AS kind,
         a.model_count, a.downloads_30d, a.downloads_all_time,
         top.top_pipeline_tag, round(top.top_n / a.model_count, 3) AS top_pipeline_share
  FROM agg a LEFT JOIN (SELECT tag, min(tag_type) AS tag_type FROM official GROUP BY 1) o USING (tag) LEFT JOIN top USING (tag)""")
# Freeform tags folded across case and separators: "Voice Conversion", "voice_conversion", "VoiceConversion".
c.sql("""CREATE TABLE variants AS
  SELECT regexp_replace(lower(tag), '[^\\p{L}\\p{N}]+', '', 'g') AS key,
         arg_max(tag, model_count) AS most_common,
         sum(model_count)::BIGINT AS model_count, count(*) AS n_variants,
         list(tag ORDER BY model_count DESC) AS variants
  FROM tags WHERE kind = 'freeform' GROUP BY 1 HAVING key <> ''""")
step("writing")
c.sql(f"COPY (SELECT * FROM tags ORDER BY model_count DESC, tag) TO '{OUT}/tags.parquet' (FORMAT parquet)")
c.sql(f"COPY (SELECT * FROM variants ORDER BY model_count DESC) TO '{OUT}/freeform_folded.parquet' (FORMAT parquet)")
c.sql(f"COPY (SELECT kind, count(*) AS distinct_tags, sum(model_count) AS taggings FROM tags GROUP BY 1 ORDER BY 2 DESC) TO '{OUT}/kinds.parquet' (FORMAT parquet)")
s = {
  "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
  "source": SRC,
  "models": c.sql("SELECT count(DISTINCT id) FROM mt").fetchone()[0],
  "distinct_tags": c.sql("SELECT count(*) FROM tags").fetchone()[0],
  "distinct_freeform": c.sql("SELECT count(*) FROM tags WHERE kind='freeform'").fetchone()[0],
  "freeform_folded_groups": c.sql("SELECT count(*) FROM variants").fetchone()[0],
  "freeform_used_once": c.sql("SELECT count(*) FROM tags WHERE kind='freeform' AND model_count=1").fetchone()[0],
  "kinds": dict(c.sql("SELECT kind, count(*) FROM tags GROUP BY 1 ORDER BY 2 DESC").fetchall()),
}
(OUT / "summary.json").write_text(json.dumps(s, indent=2))
print(json.dumps(s, indent=2))
