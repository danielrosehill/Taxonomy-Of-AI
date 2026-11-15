# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Fetch every Hugging Face model with pipeline_tag=audio-to-audio.

Source: GET https://huggingface.co/api/models (public, no auth).
Paginates via the RFC 5988 `Link: <...>; rel="next"` header (cursor-based).
Writes:
  data/models.json  full API records (every expand[] field the API accepts)
  data/models.csv   flat summary, one row per model
"""
import csv, json, re, sys, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

PIPELINE = "audio-to-audio"
# All values the endpoint accepted for expand[] as of 2026-11-15.
EXPAND = ["author", "baseModels", "cardData", "config", "createdAt", "disabled",
          "downloads", "downloadsAllTime", "evalResults", "gated", "inference",
          "inferenceProviderMapping", "lastModified", "library_name", "likes",
          "mask_token", "model-index", "pipeline_tag", "private", "safetensors",
          "sha", "siblings", "spaces", "tags", "transformersInfo", "trendingScore",
          "widgetData", "gguf", "resourceGroup", "xetEnabled"]
OUT = Path(__file__).resolve().parent.parent / "data"


def fetch_all():
    params = [("pipeline_tag", PIPELINE), ("limit", "1000"), ("sort", "createdAt")]
    params += [("expand[]", f) for f in EXPAND]
    url = "https://huggingface.co/api/models?" + urllib.parse.urlencode(params)
    models = []
    while url:
        req = urllib.request.Request(url, headers={"User-Agent": "hf-a2a-analysis"})
        with urllib.request.urlopen(req, timeout=120) as r:
            models += json.load(r)
            m = re.search(r'<([^>]+)>;\s*rel="next"', r.headers.get("Link", ""))
            url = m.group(1) if m else None
        print(f"fetched {len(models)}", file=sys.stderr)
    return models


def tag_values(tags, prefix):
    return ";".join(t[len(prefix):] for t in tags if t.startswith(prefix))


def langs(m):
    lang = (m.get("cardData") or {}).get("language") or []
    return ";".join(map(str, lang if isinstance(lang, list) else [lang]))


def main():
    models = sorted(fetch_all(), key=lambda m: m["id"].lower())
    OUT.mkdir(exist_ok=True)
    meta = {"fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "pipeline_tag": PIPELINE, "count": len(models)}
    (OUT / "models.json").write_text(json.dumps({"meta": meta, "models": models},
                                                indent=1, ensure_ascii=False))
    cols = ["id", "author", "created_at", "last_modified", "downloads_30d",
            "downloads_all_time", "likes", "trending_score", "library_name",
            "license", "languages", "base_models", "arxiv", "gated", "disabled",
            "params", "file_count", "spaces_count", "tags"]
    with open(OUT / "models.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for m in models:
            tags = m.get("tags") or []
            st = m.get("safetensors") or {}
            w.writerow([
                m["id"], m.get("author"), m.get("createdAt"), m.get("lastModified"),
                m.get("downloads"), m.get("downloadsAllTime"), m.get("likes"),
                m.get("trendingScore"), m.get("library_name"),
                tag_values(tags, "license:"),
                langs(m),
                tag_values(tags, "base_model:").replace("finetune:", "").replace("quantized:", ""),
                tag_values(tags, "arxiv:"), m.get("gated"), m.get("disabled"),
                st.get("total"), len(m.get("siblings") or []),
                len(m.get("spaces") or []), ";".join(tags),
            ])
    print(json.dumps(meta))


if __name__ == "__main__":
    main()
