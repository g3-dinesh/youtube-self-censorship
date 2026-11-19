"""STAGE 1 - Collect transcripts for a list of YouTube channels (no cookies).

Runs locally. Uses the android + web player clients to fetch caption tracks
WITHOUT a logged-in session, so you do not need to export a cookies.txt. (The
android client exposes captions without authentication; ignore_no_formats_error
lets us past the fact that it returns no video formats - we only want captions.)

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
import argparse, csv, json, os, re, sys, time, urllib.request, urllib.error
import yt_dlp

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
OUT = os.path.join(REPO, "outputs")
SLEEP = 1.8  # pause between videos to avoid HTTP 429 rate-limiting

FLAT = {"quiet": True, "skip_download": True, "no_warnings": True, "ignoreerrors": True,
        "extract_flat": True, "playlistend": 300}
# android client exposes captions without login; ignore_no_formats_error gets us
# past it returning no video formats (we only need the caption track).
META = {"quiet": True, "skip_download": True, "no_warnings": True, "ignoreerrors": True,
        "ignore_no_formats_error": True,
        "extractor_args": {"youtube": {"player_client": ["web", "android"]}}}


def list_channel_video_ids(url, cap):
    """Return up to `cap` video ids sampled evenly across the channel history."""
    with yt_dlp.YoutubeDL(FLAT) as y:
        info = y.extract_info(url, download=False)
    ids = [e["id"] for e in (info.get("entries") or []) if e and e.get("id")]
    if not ids:
        return []
    step = max(1, len(ids) / cap)          # even stride across the whole history
    return [ids[int(k * step)] for k in range(min(cap, len(ids)))]


def get_info(vid):
    try:
        with yt_dlp.YoutubeDL(META) as y:
            return y.extract_info("https://www.youtube.com/watch?v=" + vid, download=False)
    except Exception:
        return None


def caption_text(info):
    """Pull the English caption track straight from the info dict's URLs (no file)."""
    for src in (info.get("subtitles") or {}, info.get("automatic_captions") or {}):
        for lang in ("en", "en-US", "en-GB", "en-orig"):
            tr = src.get(lang)
            if not tr:
                continue
            url = next((t["url"] for t in tr if t.get("ext") == "json3"), tr[0].get("url"))
            if not url:
                continue
            for attempt in range(4):
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                    raw = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
                    data = json.loads(raw)
                    parts = [s.get("utf8", "") for ev in data.get("events", []) for s in ev.get("segs") or []]
                    return re.sub(r"\s+", " ", "".join(parts)).strip()
                except urllib.error.HTTPError as he:
                    if he.code == 429:
                        time.sleep(20 * (attempt + 1)); continue
                    break
                except Exception:
                    break
    return ""


def main():
    ap = argparse.ArgumentParser(description="Stage 1: collect channel transcripts (no cookies).")
    ap.add_argument("--channels", required=True, help="CSV with columns channel,url")
    ap.add_argument("--since-year", type=int, default=0, help="keep uploads from this year on")
    ap.add_argument("--cap", type=int, default=50, help="videos per channel")
    args = ap.parse_args()

    since = args.since_year or int(input("Collect videos from which year onward? ").strip())
    channels = list(csv.DictReader(open(args.channels, encoding="utf-8-sig")))
    os.makedirs(OUT, exist_ok=True)
    tx_path = os.path.join(OUT, "transcripts.jsonl")
    idx_path = os.path.join(OUT, "video_index.csv")

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
            for vid in ids:
                time.sleep(SLEEP)
                info = get_info(vid)
                if not info:
                    continue
                tx = caption_text(info)
                if not tx or len(tx.split()) < 50:
                    continue
                yr = (info.get("upload_date") or "")[:4]
                if yr.isdigit() and int(yr) < since:      # year filter
                    continue
                rec = {"id": vid, "channel": name, "upload_date": info.get("upload_date") or "",
                       "title": info.get("title") or "", "view_count": info.get("view_count"),
                       "transcript": tx}
                tf.write(json.dumps(rec, ensure_ascii=False) + "\n"); tf.flush()
                xw.writerow([rec["id"], name, rec["upload_date"], rec["title"], rec["view_count"]])
                kept += 1
                print(f"\r   kept {kept}", end="", flush=True)
            print()
    print(f"\nDONE. {kept} transcripts -> {tx_path}\n          video index -> {idx_path}")


if __name__ == "__main__":
    main()
