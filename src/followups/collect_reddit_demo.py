"""Small, fast DEMO of the folk-corpus collection: pull a few dated Reddit posts
about demonetisation / algospeak from the Arctic Shift archive (a cookie-free
Pushshift successor - NOT reddit.com, no login, no API key).

This is a lightweight demo of how data/folk_corpus/ was built; it fetches only a
handful of recent posts so it finishes in a few seconds.

    python src/followups/collect_reddit_demo.py            # ~10 posts
    python src/followups/collect_reddit_demo.py --limit 25 # more

Output: outputs/followups/reddit_demo_posts.jsonl
"""
import argparse
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://arctic-shift.photon-reddit.com/api/posts/search"
SUBS = ["PartneredYoutube", "youtube"]
QUERIES = ["demonetized", "algospeak", "advertiser friendly"]
UA = "academic-research-msc"
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(REPO, "outputs", "followups", "reddit_demo_posts.jsonl")


def fetch(sub, query, limit):
    url = f"{BASE}?subreddit={sub}&query={urllib.parse.quote(query)}&limit={limit}"
    for _ in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            d = json.loads(urllib.request.urlopen(req, timeout=50).read().decode("utf-8", "replace"))
            return d.get("data") or []
        except urllib.error.HTTPError as e:
            if e.code == 422:          # "slow down"
                time.sleep(6); continue
            return []
        except Exception:
            return []
    return []


def main():
    ap = argparse.ArgumentParser(description="Demo: scrape a few dated Reddit folk-theory posts (Arctic Shift).")
    ap.add_argument("--limit", type=int, default=10, help="approx. total posts to keep (default 10)")
    args = ap.parse_args()

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    seen, kept = set(), []
    per = max(2, args.limit // (len(SUBS)))
    for sub in SUBS:
        for q in QUERIES:
            if len(kept) >= args.limit:
                break
            for p in fetch(sub, q, per):
                pid = p.get("id")
                if not pid or pid in seen:
                    continue
                seen.add(pid)
                created = p.get("created_utc")
                try:
                    import datetime
                    date = datetime.datetime.utcfromtimestamp(int(created)).strftime("%Y-%m-%d") if created else ""
                except Exception:
                    date = ""
                kept.append({
                    "id": pid, "subreddit": sub, "query": q, "date": date,
                    "title": p.get("title", ""),
                    "text": (p.get("selftext") or "")[:1000],
                })
                if len(kept) >= args.limit:
                    break
            time.sleep(4)   # be polite to the archive

    with open(OUT, "w", encoding="utf-8") as fh:
        for r in kept:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"kept {len(kept)} Reddit folk-theory posts -> {OUT}")
    for r in kept[:5]:
        print(f"  [{r['date']}] r/{r['subreddit']}: {r['title'][:70]}")


if __name__ == "__main__":
    main()
