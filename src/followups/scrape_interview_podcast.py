"""Collect #1 interview transcripts + #3 main-vs-podcast channel pairs (local).
Writes to data/metadiscourse.jsonl (type=interview) and data/podcast_pairs.jsonl.
"""
import json, os, re, time, urllib.request, urllib.error
import yt_dlp
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
META_OUT = os.path.join(REPO, "data", "metadiscourse.jsonl")
PAIR_OUT = os.path.join(REPO, "data", "podcast_pairs.jsonl")

INTERVIEW = [  # creators interviewing creators about the creator economy / demonetisation
    "https://www.youtube.com/@ColinandSamir/videos",
    "https://www.youtube.com/@CreatorSupport/videos",
]
# #3 pairs: (creator, role, channel_url) - same person, main vs podcast/2nd channel
PAIRS = [
    ("h3", "main",    "https://www.youtube.com/@h3h3Productions/videos"),
    ("h3", "podcast", "https://www.youtube.com/@H3Podcast/videos"),
    ("cr1tikal", "main",    "https://www.youtube.com/@penguinz0/videos"),
    ("cr1tikal", "podcast", "https://www.youtube.com/@MoistCr1TiKaL/videos"),
    ("colinsamir", "main",    "https://www.youtube.com/@ColinandSamir/videos"),
]
CAP = 25
FLAT = {"quiet": True, "skip_download": True, "no_warnings": True, "ignoreerrors": True,
        "extract_flat": True, "playlistend": 40}
METAY = {"quiet": True, "skip_download": True, "no_warnings": True, "ignoreerrors": True,
         "ignore_no_formats_error": True,
         "extractor_args": {"youtube": {"player_client": ["web", "android"]}}}
DEMON = re.compile(r"\b(monetis|monetiz|demonetis|demonetiz|adsense|advertiser|ad revenue|"
                   r"yellow dollar|limited ads|sponsor|algorithm|cant say|censor|unalive)\b", re.I)


def captions(info):
    for src in (info.get("subtitles") or {}, info.get("automatic_captions") or {}):
        for lang in ("en", "en-US", "en-GB", "en-orig"):
            tr = src.get(lang)
            if not tr: continue
            url = next((t["url"] for t in tr if t.get("ext") == "json3"), tr[0].get("url"))
            if not url: continue
            for a in range(3):
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                    raw = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
                    d = json.loads(raw)
                    return re.sub(r"\s+", " ", "".join(s.get("utf8", "") for ev in d.get("events", []) for s in ev.get("segs") or [])).strip()
                except urllib.error.HTTPError as he:
                    if he.code == 429: time.sleep(15*(a+1)); continue
                    break
                except Exception: break
    return ""


def list_ids(url):
    with yt_dlp.YoutubeDL(FLAT) as y:
        info = y.extract_info(url, download=False)
    return [(e.get("id"), e.get("title", "")) for e in (info.get("entries") or []) if e and e.get("id")][:CAP]


def getinfo(vid):
    try:
        with yt_dlp.YoutubeDL(METAY) as y:
            return y.extract_info("https://www.youtube.com/watch?v=" + vid, download=False)
    except Exception:
        return None


def done_ids(path, key="id"):
    s = set()
    if os.path.exists(path):
        for l in open(path, encoding="utf-8"):
            try: s.add(json.loads(l)[key])
            except: pass
    return s


def main():
    # ---- #1 interviews (only keep videos that actually discuss monetisation) ----
    dm = done_ids(META_OUT)
    fm = open(META_OUT, "a", encoding="utf-8"); k1 = 0
    for url in INTERVIEW:
        try: ents = list_ids(url)
        except Exception as e: print("iv chan fail", str(e)[:50], flush=True); continue
        print(f"[interview] {url.split('@')[1].split('/')[0]} -> {len(ents)}", flush=True)
        for vid, title in ents:
            if not vid or vid in dm: continue
            dm.add(vid)
            if not DEMON.search(title or ""):
                # still check desc/transcript below if title ambiguous, but skip obvious non-topic
                pass
            time.sleep(1.4); info = getinfo(vid)
            if not info: continue
            tx = captions(info)
            if not tx or len(tx.split()) < 150: continue
            if not DEMON.search(title + " " + (info.get("description") or "")[:600] + " " + tx[:4000]):
                continue
            fm.write(json.dumps({"id": vid, "type": "interview", "query": "channel-iv",
                "channel": info.get("channel", ""), "upload_date": info.get("upload_date", ""),
                "title": title, "description": (info.get("description") or "")[:1500],
                "transcript": tx}, ensure_ascii=False) + "\n"); fm.flush(); k1 += 1
            print(f"   iv kept {k1}: {title[:50]}", flush=True)
    fm.close()

    # ---- #3 main vs podcast pairs ----
    dp = done_ids(PAIR_OUT)
    fp = open(PAIR_OUT, "a", encoding="utf-8"); k3 = 0
    for creator, role, url in PAIRS:
        try: ents = list_ids(url)
        except Exception as e: print("pair chan fail", str(e)[:50], flush=True); continue
        print(f"[pair] {creator}/{role} -> {len(ents)}", flush=True)
        for vid, title in ents:
            if not vid or vid in dp: continue
            dp.add(vid)
            time.sleep(1.4); info = getinfo(vid)
            if not info: continue
            tx = captions(info)
            if not tx or len(tx.split()) < 150: continue
            fp.write(json.dumps({"id": vid, "creator": creator, "role": role,
                "channel": info.get("channel", ""), "title": title,
                "transcript": tx}, ensure_ascii=False) + "\n"); fp.flush(); k3 += 1
            if k3 % 10 == 0: print(f"   pair kept {k3}", flush=True)
    fp.close()
    print(f"DONE. interviews +{k1} -> metadiscourse ; pairs +{k3} -> podcast_pairs.jsonl")


if __name__ == "__main__":
    main()
