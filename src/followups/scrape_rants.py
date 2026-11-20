"""Scrape 'my channel got demonetized' post-mortem rants (#2 cause-extraction cohort).

Sources:
  - two user-supplied playlists
  - several ytsearch queries for creators narrating their own demonetisation
Keeps videos whose title OR transcript actually discusses demonetisation, >=120 words.
Appends to data/metadiscourse.jsonl with type=rant.
"""
import json, os, re, sys, time, urllib.request, urllib.error
import yt_dlp
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(REPO, "data", "rants.jsonl")

PLAYLISTS = [
    "https://youtube.com/playlist?list=PLTZaOylOgJT-R8U0lD7_zqBXRjrCUVSfo",
    "https://youtube.com/playlist?list=PL2TVEkr1lWII0molm3-ulYmY3H1TXZ_HZ",
]
QUERIES = [
    "my channel got demonetized", "why my channel was demonetized",
    "youtube demonetized me", "i got demonetized storytime",
    "demonetized my video why", "youtube took my monetization",
    "got the yellow dollar demonetized", "my video got limited ads",
]
PER_SEARCH = 25
DEMON = re.compile(r"\b(demonetis|demonetiz|monetis|monetiz|yellow dollar|limited ads|"
                   r"ad[- ]?sense|advertiser[- ]?friendly|took my monetization|"
                   r"lost monetization|ad revenue|strike|guidelines)\b", re.I)
FLAT = {"quiet": True, "skip_download": True, "no_warnings": True, "ignoreerrors": True,
        "extract_flat": True, "playlistend": 100}
METAY = {"quiet": True, "skip_download": True, "no_warnings": True, "ignoreerrors": True,
         "ignore_no_formats_error": True,
         "extractor_args": {"youtube": {"player_client": ["web", "android"]}}}


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


def flat_ids(url):
    with yt_dlp.YoutubeDL(FLAT) as y:
        info = y.extract_info(url, download=False)
    return [(e.get("id"), e.get("title", "")) for e in (info.get("entries") or []) if e and e.get("id")]


def getinfo(vid):
    try:
        with yt_dlp.YoutubeDL(METAY) as y:
            return y.extract_info("https://www.youtube.com/watch?v=" + vid, download=False)
    except Exception:
        return None


def main():
    done = set()
    if os.path.exists(OUT):
        for l in open(OUT, encoding="utf-8"):
            try: done.add(json.loads(l)["id"])
            except: pass
    fh = open(OUT, "a", encoding="utf-8"); kept = 0

    # gather candidate (id,title,source) list
    cands = []
    for pl in PLAYLISTS:
        try:
            ents = flat_ids(pl)
            print(f"[playlist] -> {len(ents)} entries", flush=True)
            cands += [(i, t, "playlist") for i, t in ents]
        except Exception as e:
            print("playlist fail", str(e)[:60], flush=True)
    for q in QUERIES:
        try:
            ents = flat_ids(f"ytsearch{PER_SEARCH}:{q}")
            print(f"[search] {q!r} -> {len(ents)}", flush=True)
            cands += [(i, t, "search") for i, t in ents]
        except Exception as e:
            print("search fail", q, str(e)[:50], flush=True)

    seen = set()
    for vid, title, srctag in cands:
        if not vid or vid in done or vid in seen: continue
        seen.add(vid)
        time.sleep(1.3)
        info = getinfo(vid)
        if not info: continue
        tx = captions(info)
        if not tx or len(tx.split()) < 120: continue
        if not DEMON.search((title or "") + " " + tx[:5000]):
            continue
        rec = {"id": vid, "type": "rant", "query": srctag,
               "channel": info.get("channel", ""), "upload_date": info.get("upload_date", ""),
               "title": title, "description": (info.get("description") or "")[:1500],
               "transcript": tx}
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n"); fh.flush(); kept += 1
        print(f"   rant kept {kept}: {title[:55]}", flush=True)
    fh.close()
    print(f"DONE. +{kept} rant transcripts -> {OUT}")


if __name__ == "__main__":
    main()
