"""STAGE 3 - Fetch one video's transcript + details by video ID (no cookies).

For building the hand-labelled set: you watch a video, confirm whether it is
monetised or demonetised, then run this to pull its transcript and metadata into
one JSON record you can drop into data/dataset/<creator>/ and add to
data/ground_truth_labels.csv.

Uses the android + web player clients, so no cookies.txt is needed.

Input
  a single video id (argument, or you are prompted for it)

Output
  prints a summary, and writes outputs/single_<id>.json with:
  id, channel, upload_date, title, duration, view_count, like_count,
  comment_count, tags, transcript

Example
  python src/03_fetch_single_video.py dQw4w9WgXcQ
"""
import json, os, re, sys, time, urllib.request, urllib.error
import yt_dlp

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
OUT = os.path.join(REPO, "outputs")
META = {"quiet": True, "skip_download": True, "no_warnings": True, "ignoreerrors": True,
        "ignore_no_formats_error": True,
        "extractor_args": {"youtube": {"player_client": ["web", "android"]}}}


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
    vid = (sys.argv[1] if len(sys.argv) > 1 else input("Video ID: ").strip())
    with yt_dlp.YoutubeDL(META) as y:
        info = y.extract_info("https://www.youtube.com/watch?v=" + vid, download=False)
    if not info:
        sys.exit("could not fetch video info")
    transcript = caption_text(info)

    rec = {"id": vid, "slug": info.get("channel", ""), "channel": info.get("channel", ""),
           "upload_date": info.get("upload_date", ""), "title": info.get("title", ""),
           "duration": info.get("duration"), "view_count": info.get("view_count"),
           "like_count": info.get("like_count"), "comment_count": info.get("comment_count"),
           "tags": info.get("tags") or [], "transcript": transcript}

    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"single_{vid}.json")
    json.dump(rec, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print("=" * 60)
    print("title :", rec["title"])
    print("channel:", rec["channel"], "| date:", rec["upload_date"], "| views:", rec["view_count"])
    print("words in transcript:", len(transcript.split()))
    print("saved ->", path)
    print("\nNext: confirm monetised/demonetised by watching, then add a row to "
          "data/ground_truth_labels.csv (video_id,creator,label,mechanism).")


if __name__ == "__main__":
    main()
