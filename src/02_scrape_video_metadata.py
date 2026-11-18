"""STAGE 2 - Scrape engagement metadata for collected videos.

Takes the video_index.csv produced by Stage 1 (or any CSV with a `video_id` /
`id` column) and fetches each video's public engagement signals with yt-dlp.

Input
  --index   CSV with a video id column (default: outputs/video_index.csv)
  --comments N   also pull up to N top comments per video (slow; default 0 = off)

Output
  outputs/video_metadata.csv   id, channel, upload_date, duration_sec, view_count,
                               like_count, comment_count, tags, categories
  (+ outputs/video_comments.jsonl if --comments N is used)

Example
  python src/02_scrape_video_metadata.py --index outputs/video_index.csv
  python src/02_scrape_video_metadata.py --index outputs/video_index.csv --comments 20
"""
import argparse, csv, json, os, time
import yt_dlp

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
OUT = os.path.join(REPO, "outputs")
COOKIEFILE = os.path.join(REPO, "data", "www.youtube.com_cookies.txt")
_CK = {"cookiefile": COOKIEFILE} if os.path.exists(COOKIEFILE) else {}
SLEEP = 1.2


def read_ids(path):
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    out = []
    for r in rows:
        vid = (r.get("video_id") or r.get("id") or "").strip()
        if vid:
            out.append((vid, r.get("channel", "")))
    return out


def fetch_meta(vid, want_comments):
    opts = {"quiet": True, "skip_download": True, "no_warnings": True,
            "ignoreerrors": True, "getcomments": bool(want_comments), **_CK}
    try:
        with yt_dlp.YoutubeDL(opts) as y:
            return y.extract_info("https://www.youtube.com/watch?v=" + vid, download=False)
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser(description="Stage 2: scrape video engagement metadata.")
    ap.add_argument("--index", default=os.path.join(OUT, "video_index.csv"))
    ap.add_argument("--comments", type=int, default=0, help="top comments per video to save")
    args = ap.parse_args()

    ids = read_ids(args.index)
    os.makedirs(OUT, exist_ok=True)
    meta_path = os.path.join(OUT, "video_metadata.csv")
    cmt_path = os.path.join(OUT, "video_comments.jsonl")
    cf = open(cmt_path, "w", encoding="utf-8") if args.comments else None

    with open(meta_path, "w", newline="", encoding="utf-8") as mf:
        w = csv.writer(mf)
        w.writerow(["id", "channel", "upload_date", "duration_sec", "view_count",
                    "like_count", "comment_count", "tags", "categories"])
        for i, (vid, chan) in enumerate(ids, 1):
            time.sleep(SLEEP)
            info = fetch_meta(vid, args.comments)
            if not info:
                print(f"[{i}/{len(ids)}] {vid} failed"); continue
            w.writerow([vid, chan or info.get("channel", ""), info.get("upload_date", ""),
                        info.get("duration"), info.get("view_count"),
                        info.get("like_count"), info.get("comment_count"),
                        "|".join(info.get("tags") or []),
                        "|".join(info.get("categories") or [])])
            if cf:
                for c in (info.get("comments") or [])[:args.comments]:
                    cf.write(json.dumps({"video_id": vid, "author": c.get("author"),
                                         "text": c.get("text"), "likes": c.get("like_count")},
                                        ensure_ascii=False) + "\n")
            print(f"[{i}/{len(ids)}] {vid}  views={info.get('view_count')} "
                  f"likes={info.get('like_count')} comments={info.get('comment_count')}")
    if cf:
        cf.close()
    print(f"\nDONE -> {meta_path}" + (f"\n     -> {cmt_path}" if args.comments else ""))


if __name__ == "__main__":
    main()
