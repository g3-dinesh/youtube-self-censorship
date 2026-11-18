"""STAGE 1 - Collect transcripts for a list of YouTube channels.

Runs LOCALLY on your own machine (your IP, your logged-in Chrome session via an
exported cookies.txt), which is what lets YouTube hand over caption tracks.

Input
  --channels  CSV with columns: channel,url   (one row per creator)
              e.g.  pakman,https://www.youtube.com/@thedavidpakmanshow/videos
  --since-year  only keep videos uploaded in this year or later
                (if omitted, you are prompted for it)
  --cap       max videos sampled per channel (default 50), spread evenly across
              the channel's upload history

Output (into outputs/)
  transcripts.jsonl   one line per video: id, channel, upload_date, title,
                      view_count, transcript
  video_index.csv     id, channel, upload_date, title, view_count
                      (feeds Stage 2 - scrape_video_metadata.py)

Example
  python src/01_collect_channel_transcripts.py --channels data/sample_channels.csv --since-year 2021
"""
import argparse, csv, glob, json, os, re, sys, tempfile, time
import yt_dlp

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
OUT = os.path.join(REPO, "outputs")
# Chrome 127+ encrypts its cookie DB, so point this at an exported cookies.txt
# (use the "Get cookies.txt LOCALLY" extension while logged into youtube.com).
COOKIEFILE = os.path.join(REPO, "data", "www.youtube.com_cookies.txt")
_CK = {"cookiefile": COOKIEFILE} if os.path.exists(COOKIEFILE) else {}
SLEEP = 1.8  # pause between videos to avoid HTTP 429 rate-limiting


def list_channel_video_ids(url, cap):
    """Return up to `cap` video ids sampled evenly across the channel history."""
    flat = {"quiet": True, "skip_download": True, "no_warnings": True,
            "ignoreerrors": True, "extract_flat": True, "playlistend": 300, **_CK}
    with yt_dlp.YoutubeDL(flat) as y:
        info = y.extract_info(url, download=False)
    ids = [e["id"] for e in (info.get("entries") or []) if e and e.get("id")]
    if not ids:
        return []
    step = max(1, len(ids) / cap)          # even stride across the whole history
    return [ids[int(k * step)] for k in range(min(cap, len(ids)))]


def parse_json3(path):
    """Turn a downloaded json3 caption file into plain transcript text."""
    try:
        j = json.load(open(path, encoding="utf-8"))
    except Exception:
        return ""
    parts = [s.get("utf8", "") for ev in j.get("events", []) for s in ev.get("segs") or []]
    return re.sub(r"\s+", " ", "".join(parts)).strip()


def fetch_one(vid, tmp):
    """Download one video's English captions + metadata. Returns a record or None."""
    opts = {"quiet": True, "skip_download": True, "no_warnings": True,
            "ignoreerrors": True, "writeautomaticsub": True, "writesubtitles": True,
            "subtitleslangs": ["en", "en-orig", "en-US"], "subtitlesformat": "json3",
            "socket_timeout": 45, "retries": 3,
            "outtmpl": os.path.join(tmp, "%(id)s.%(ext)s"), **_CK}
    try:
        with yt_dlp.YoutubeDL(opts) as y:
            info = y.extract_info("https://www.youtube.com/watch?v=" + vid, download=True)
    except Exception:
        info = None
    files = glob.glob(os.path.join(tmp, vid + "*.json3"))
    tx = parse_json3(files[0]) if files else ""
    for f in glob.glob(os.path.join(tmp, vid + "*")):      # tidy up temp files
        try: os.remove(f)
        except Exception: pass
    if not info or not tx or len(tx.split()) < 50:
        return None
    return {"id": vid, "upload_date": info.get("upload_date") or "",
            "title": info.get("title") or "", "view_count": info.get("view_count"),
            "transcript": tx}


def main():
    ap = argparse.ArgumentParser(description="Stage 1: collect channel transcripts.")
    ap.add_argument("--channels", required=True, help="CSV with columns channel,url")
    ap.add_argument("--since-year", type=int, default=0, help="keep uploads from this year on")
    ap.add_argument("--cap", type=int, default=50, help="videos per channel")
    args = ap.parse_args()

    since = args.since_year or int(input("Collect videos from which year onward? ").strip())
    channels = list(csv.DictReader(open(args.channels, encoding="utf-8-sig")))
    os.makedirs(OUT, exist_ok=True)
    tx_path = os.path.join(OUT, "transcripts.jsonl")
    idx_path = os.path.join(OUT, "video_index.csv")
    tmp = tempfile.mkdtemp()

    kept = 0
    with open(tx_path, "w", encoding="utf-8") as tf, \
         open(idx_path, "w", newline="", encoding="utf-8") as xf:
        xw = csv.writer(xf)
        xw.writerow(["id", "channel", "upload_date", "title", "view_count"])
        for row in channels:
            name, url = row["channel"].strip(), row["url"].strip()
            try:
                ids = list_channel_video_ids(url, args.cap)
            except Exception as e:
                print(f"{name}: channel list failed ({str(e)[:60]})"); continue
            print(f"{name}: sampling {len(ids)} videos (since {since})...", flush=True)
            for i, vid in enumerate(ids, 1):
                time.sleep(SLEEP)
                rec = fetch_one(vid, tmp)
                if not rec:
                    continue
                yr = rec["upload_date"][:4]
                if yr.isdigit() and int(yr) < since:      # year filter
                    continue
                rec["channel"] = name
                tf.write(json.dumps(rec, ensure_ascii=False) + "\n"); tf.flush()
                xw.writerow([rec["id"], name, rec["upload_date"], rec["title"], rec["view_count"]])
                kept += 1
                print(f"\r   kept {kept}", end="", flush=True)
            print()
    print(f"\nDONE. {kept} transcripts -> {tx_path}\n          video index -> {idx_path}")


if __name__ == "__main__":
    main()
