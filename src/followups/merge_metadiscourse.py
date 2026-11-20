"""Merge the scraped rant + advice cohorts into data/metadiscourse.jsonl,
deduping by video id. Idempotent. Used before the #1/#2 LLM passes.

Inputs : data/metadiscourse.jsonl (existing), data/rants.jsonl, data/advice.jsonl
Output : rewrites data/metadiscourse.jsonl ; prints type counts.
"""
import json, os, collections
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
D = os.path.join(REPO, "data")


def main():
    seen, out = set(), []
    main_path = os.path.join(D, "metadiscourse.jsonl")
    if os.path.exists(main_path):
        for l in open(main_path, encoding="utf-8"):
            try: r = json.loads(l)
            except Exception: continue
            if r["id"] in seen: continue
            seen.add(r["id"]); out.append(r)
    added = collections.Counter()
    for fn in ("rants.jsonl", "advice.jsonl"):
        p = os.path.join(D, fn)
        if not os.path.exists(p):
            continue
        for l in open(p, encoding="utf-8"):
            try: r = json.loads(l)
            except Exception: continue
            if r["id"] in seen: continue
            seen.add(r["id"]); out.append(r); added[r.get("type", "?")] += 1
    with open(main_path, "w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("added:", dict(added))
    print("metadiscourse now:", dict(collections.Counter(r.get("type") for r in out)))


if __name__ == "__main__":
    main()
