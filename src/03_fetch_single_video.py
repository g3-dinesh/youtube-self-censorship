"""STAGE 3 - Fetch one video's transcript + details by video ID.

For building the hand-labelled set: you watch a video, confirm whether it is
monetised or demonetised, then run this to pull its transcript and metadata into
one JSON record you can drop into data/dataset/<creator>/ and add to
data/ground_truth_labels.csv.

Input
  a single video id (argument, or you are prompted for it)

Output
  prints a summary, and writes outputs/single_<id>.json with:
  id, channel, upload_date, title, duration, view_count, like_count,
  comment_count, tags, transcript

Example
  python src/03_fetch_single_video.py dQw4w9WgXcQ
"""
import json, os, re, sys, glob, tempfile
import yt_dlp

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
OUT = os.path.join(REPO, "outputs")
COOKIEFILE = os.path.join(REPO, "data", "www.youtube.com_cookies.txt")
_CK = {"cookiefile": COOKIEFILE} if os.path.exists(COOKIEFILE) else {}


def parse_json3(path):
    try:
        j = json.load(open(path, encoding="utf-8"))
    except Exception:
        return ""
    parts = [s.get("utf8", "") for ev in j.get("events", []) for s in ev.get("segs") or []]
    return re.sub(r"\s+", " ", "".join(parts)).strip()


def main():
    vid = (sys.argv[1] if len(sys.argv) > 1 else input("Video ID: ").strip())
    tmp = tempfile.mkdtemp()
    opts = {"quiet": True, "skip_download": True, "no_warnings": True,
            "ignoreerrors": True, "writeautomaticsub": True, "writesubtitles": True,
            "subtitleslangs": ["en", "en-orig", "en-US"], "subtitlesformat": "json3",
            "outtmpl": os.path.join(tmp, "%(id)s.%(ext)s"), **_CK}
    with yt_dlp.YoutubeDL(opts) as y:
        info = y.extract_info("https://www.youtube.com/watch?v=" + vid, download=True)
    files = glob.glob(os.path.join(tmp, vid + "*.json3"))
    transcript = parse_json3(files[0]) if files else ""

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
