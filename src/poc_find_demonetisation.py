import argparse
import csv
import glob
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(HERE, "..", "data", "dataset")
DEFAULT_OUT = os.path.join(HERE, "..", "data", "experiments",
                           "demonetisation_selfreport.csv")

DEMON_TERMS = [
    "demonetiz", "demonetis", "de-monetiz", "de-monetis",
    "advertiser friendly", "advertiser-friendly", "ad friendly", "ad-friendly",
    "adpocalypse", "yellow dollar", "yellow icon", "yellow $",
    "yellow dollar sign", "little yellow", "got the yellow",
    "no ads on this", "no ads running", "ads got pulled", "pulled the ads",
    "removed ads", "limited ads", "not suitable for advertisers",
    "not advertiser friendly", "age restrict", "age-restrict",
    "community guidelines strike", "youtube strike", "got a strike",
    "youtube censor", "censored by youtube", "youtube won't let",
    "youtube wont let", "can't say", "cant say", "shadow ban", "shadowban",
    "monetization", "monetisation",
]

CREATOR_STRONG = [
    "demonetiz", "demonetis", "this video is demon", "got demon",
    "this got demon", "we got demon", "was demonetiz", "been demonetiz",
    "youtube demonetiz", "no ads on this", "pulled the ads", "ads got pulled",
    "yellow dollar", "got the yellow", "limited ads", "age restrict",
    "youtube won't let", "youtube wont let",
]

WINDOW = 90


def find_snippets(blob, terms, limit=3):
    low = (blob or "").lower()
    hits = []
    seen = set()
    for t in terms:
        start = 0
        while True:
            i = low.find(t, start)
            if i < 0:
                break
            a = max(0, i - WINDOW)
            b = min(len(blob), i + len(t) + WINDOW)
            snip = re.sub(r"\s+", " ", blob[a:b]).strip()
            key = snip.lower()
            if key not in seen:
                seen.add(key)
                hits.append((t, snip))
            start = i + len(t)
            if len(hits) >= limit:
                return hits
    return hits


def creator_name(rec):
    return (rec.get("channel") or rec.get("slug") or "").strip().lower()


def scan_comments(rec):
    channel = creator_name(rec)
    n_viewer = 0
    n_creator = 0
    top = None
    top_by_creator = False
    for c in rec.get("comments") or []:
        text = c.get("text") or ""
        low = text.lower()
        if not any(t in low for t in DEMON_TERMS):
            continue
        author = (c.get("author") or "").strip().lower().lstrip("@")
        is_creator = bool(channel) and (author in channel or channel in author)
        if is_creator:
            n_creator += 1
        else:
            n_viewer += 1
        likes = c.get("like_count") or 0
        if top is None or is_creator or likes > (top[0] if top else -1):
            top = (likes, re.sub(r"\s+", " ", text).strip()[:280])
            top_by_creator = is_creator
    return n_viewer, n_creator, (top[1] if top else ""), top_by_creator


def score_row(r):
    s = 0
    if r["creator_transcript_mention"]:
        s += 5
    if r["creator_comment_mention"]:
        s += 4
    if r["desc_mention"]:
        s += 2
    s += min(r["viewer_comment_mentions"], 10)
    return s


def main():
    ap = argparse.ArgumentParser(
        description="Surface videos whose CREATOR or COMMENTS self-report a "
                    "monetisation problem (demonetised / limited ads / age "
                    "restricted / 'can't say'). Scans transcript, description and "
                    "the collected comments of every dataset video and ranks the "
                    "self-reported cases with the evidence snippet. This is a weak "
                    "self-report label channel, independent of the ad sampler.")
    ap.add_argument("--dataset", default=DATASET_DIR)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--min-score", type=int, default=1,
                    help="only keep videos with at least this evidence score")
    args = ap.parse_args()

    files = glob.glob(os.path.join(args.dataset, "*", "*.json"))
    rows = []
    scanned = 0
    for path in files:
        try:
            rec = json.load(open(path, encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(rec, dict) or not rec.get("id"):
            continue
        scanned += 1
        transcript = rec.get("transcript") or ""
        desc = rec.get("description") or ""
        title = rec.get("title") or ""

        t_hits = find_snippets(title + ". " + transcript, CREATOR_STRONG)
        d_hits = find_snippets(desc, DEMON_TERMS)
        n_viewer, n_creator, top_comment, top_by_creator = scan_comments(rec)

        row = {
            "video_id": rec.get("id"),
            "creator": rec.get("slug", ""),
            "title": title[:100],
            "url": rec.get("url", ""),
            "creator_transcript_mention": 1 if t_hits else 0,
            "desc_mention": 1 if d_hits else 0,
            "creator_comment_mention": 1 if n_creator else 0,
            "viewer_comment_mentions": n_viewer,
            "terms": "|".join(sorted({t for t, _ in t_hits + d_hits})),
            "transcript_evidence": (t_hits[0][1] if t_hits else ""),
            "comment_evidence": top_comment,
            "comment_evidence_by_creator": 1 if top_by_creator else 0,
        }
        row["evidence_score"] = score_row(row)
        if row["evidence_score"] >= args.min_score:
            rows.append(row)

    rows.sort(key=lambda r: r["evidence_score"], reverse=True)

    fields = ["video_id", "creator", "title", "url", "evidence_score",
              "creator_transcript_mention", "creator_comment_mention",
              "desc_mention", "viewer_comment_mentions", "terms",
              "transcript_evidence", "comment_evidence",
              "comment_evidence_by_creator"]
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    n_creator_t = sum(r["creator_transcript_mention"] for r in rows)
    n_creator_c = sum(r["creator_comment_mention"] for r in rows)
    n_viewer = sum(1 for r in rows if r["viewer_comment_mentions"])
    print(f"scanned {scanned} videos")
    print(f"self-report candidates: {len(rows)}")
    print(f"  creator says it in transcript/title: {n_creator_t}")
    print(f"  creator says it in a comment:        {n_creator_c}")
    print(f"  viewers mention it in comments:      {n_viewer}")
    print(f"-> {args.out}")
    print("\ntop 15 by evidence:")
    for r in rows[:15]:
        src = []
        if r["creator_transcript_mention"]:
            src.append("transcript")
        if r["creator_comment_mention"]:
            src.append("creator-comment")
        if r["viewer_comment_mentions"]:
            src.append(f"{r['viewer_comment_mentions']}x viewer")
        print(f"  [{r['evidence_score']:2}] {r['video_id']:14} {r['creator']:10} "
              f"{','.join(src)}")


if __name__ == "__main__":
    main()
