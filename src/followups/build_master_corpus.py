"""Build data/master_transcripts.jsonl — the unified corpus the follow-up
experiments run on. It is the UNION of:
  * data/euph_transcripts.jsonl   (euphemism-genre transcripts)
  * data/dataset/<creator>/*.json (the labelled dataset)
deduplicated by video id and filtered to >= 50 transcript words.

This file is regenerated (not committed) to avoid duplicating data already in
the repo. Run it once before the corpus-level follow-up scripts
(cs_leaky_proximity, cs_detector_compare, per_creator_masking).

    python src/followups/build_master_corpus.py
"""
import glob
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(REPO, "data")
OUT = os.path.join(DATA, "master_transcripts.jsonl")
MINWORDS = 50


def row(d, src):
    cat = d.get("category")
    if not cat:
        cats = d.get("categories")
        cat = cats[0] if isinstance(cats, list) and cats else None
    return {
        "id": d.get("id"),
        "channel": d.get("channel", ""),
        "category": cat,
        "title": d.get("title", ""),
        "description": (d.get("description") or "")[:2000],
        "upload_date": d.get("upload_date", ""),
        "live_ads": d.get("live_ads"),
        "view_count": d.get("view_count"),
        "transcript": d.get("transcript", "") or "",
        "src": src,
    }


def main():
    seen, out = set(), []
    # 1) euphemism corpus
    ep = os.path.join(DATA, "euph_transcripts.jsonl")
    if os.path.exists(ep):
        for l in open(ep, encoding="utf-8"):
            try: d = json.loads(l)
            except Exception: continue
            if not d.get("id") or d["id"] in seen:
                continue
            if len((d.get("transcript") or "").split()) < MINWORDS:
                continue
            seen.add(d["id"]); out.append(row(d, "euph"))
    # 2) labelled dataset
    for f in glob.glob(os.path.join(DATA, "dataset", "*", "*.json")):
        try: d = json.load(open(f, encoding="utf-8"))
        except Exception: continue
        if not d.get("id") or d["id"] in seen:
            continue
        if len((d.get("transcript") or "").split()) < MINWORDS:
            continue
        seen.add(d["id"]); out.append(row(d, "dataset"))

    with open(OUT, "w", encoding="utf-8") as fh:
        for r in out:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    chans = len({r["channel"] for r in out})
    print(f"master corpus: {len(out)} videos, {chans} channels -> {OUT}")


if __name__ == "__main__":
    main()
