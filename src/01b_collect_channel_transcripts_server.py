"""STAGE 1 (server variant) - Collect channel transcripts on a remote machine (optional).

Same job as 01_collect_channel_transcripts.py, but tuned for running on a
server with NO browser cookies and a different IP. This is the variant that
actually collected most of the project corpus (it runs detached in tmux so it
survives SSH drops). Differences from the local version:
  - no cookies (uses the android/web player client instead of a login)
  - forces the web + android player clients and ignore_no_formats_error, because
    the android client returns no video formats but still exposes captions
  - longer 429 backoff, emits a `category` tag per channel
  - CAP is read from the environment; an optional seen-ids file skips videos
    already collected (so a re-run only adds new ones)

Input
  argv[1]  channels JSON: a list of {"channel","category","url"} objects
  argv[2]  (optional) path to a file of video ids already collected, one per line
  env CAP  videos sampled per channel (default 50)

Output (stdout, one JSON object per video)
  {channel, category, id, upload_date, title, view_count, transcript}

Example (on the remote machine)
  CAP=150 python3 01b_collect_channel_transcripts_server.py channels.json seen.txt > out.jsonl
"""
import json, os, re, sys, time, urllib.request
import yt_dlp

CAP = int(os.environ.get("CAP", "50"))
SLEEP = 1.8   # between videos, to avoid 429 rate-limiting
# optional 2nd arg: a file of video ids already collected (one per line) to SKIP
SEEN = set()
if len(sys.argv) > 2 and os.path.exists(sys.argv[2]):
    SEEN = {ln.strip() for ln in open(sys.argv[2]) if ln.strip()}

FLAT = {"quiet": True, "skip_download": True, "no_warnings": True, "ignoreerrors": True,
        "extract_flat": True, "playlistend": 300}
# ignore_no_formats_error: the android client returns no video formats, which
# otherwise raises before we reach the captions. We only need captions.
META = {"quiet": True, "skip_download": True, "no_warnings": True, "ignoreerrors": True,
        "ignore_no_formats_error": True,
        "extractor_args": {"youtube": {"player_client": ["web", "android"]}}}


def get_info(vid):
    try:
        with yt_dlp.YoutubeDL(META) as y:
            return y.extract_info("https://www.youtube.com/watch?v=" + vid, download=False)
    except Exception:
        return None


def caption_text(info):
    for src in (info.get("subtitles") or {}, info.get("automatic_captions") or {}):
        for lang in ("en", "en-US", "en-GB", "en-orig"):
            tr = src.get(lang)
            if tr:
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
    chans = json.load(open(sys.argv[1], encoding="utf-8"))
    for c in chans:
        name = c["channel"]
        try:
            with yt_dlp.YoutubeDL(FLAT) as y:
                info = y.extract_info(c["url"], download=False)
            ids = [e["id"] for e in (info.get("entries") or []) if e and e.get("id")]
        except Exception as ex:
            sys.stderr.write(f"{name}: list err {str(ex)[:60]}\n"); sys.stderr.flush(); continue
        N = len(ids)
        if N == 0:
            sys.stderr.write(f"{name}: 0 videos listed\n"); sys.stderr.flush(); continue
        step = max(1, N / CAP)
        picks = [ids[int(k * step)] for k in range(min(CAP, N))]
        picks = [v for v in dict.fromkeys(picks) if v not in SEEN]   # dedup + skip collected
        got = 0
        for vid in picks:
            time.sleep(SLEEP)
            vi = get_info(vid)
            if not vi:
                continue
            tx = caption_text(vi)
            if not tx or len(tx.split()) < 50:
                continue
            rec = {"channel": name, "category": c.get("category", ""), "id": vid,
                   "upload_date": vi.get("upload_date") or "", "title": vi.get("title") or "",
                   "view_count": vi.get("view_count"), "transcript": tx}
            sys.stdout.write(json.dumps(rec, ensure_ascii=False) + "\n"); sys.stdout.flush()
            got += 1
        sys.stderr.write(f"{name}: {got}/{len(picks)} collected (hist N={N})\n"); sys.stderr.flush()


if __name__ == "__main__":
    main()
