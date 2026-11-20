"""Scrape 'how to avoid demonetization' ADVICE videos (#1 stated-rules cohort).

These are creators TELLING OTHER CREATORS what to avoid -> their explicit folk
rules. Feeds the walk-vs-talk / folk-theory-alignment analysis: what rules they
STATE vs what the written policy actually says.

Appends to data/advice.jsonl with type=advice. Keeps advisory videos with
>=150-word captions that discuss monetisation rules.
"""
import json, os, re, time, urllib.request, urllib.error
import yt_dlp
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(REPO, "data", "advice.jsonl")

QUERIES = [
    "how to avoid demonetization youtube", "words you can't say on youtube",
    "how to be advertiser friendly youtube", "youtube monetization rules explained",
    "what gets you demonetized youtube", "advertiser friendly guidelines tips",
    "how to not get demonetized", "youtube self censor words tips",
    "how to talk about sensitive topics youtube monetization",
    "youtube limited ads how to avoid", "stay monetized youtube tips",
    "algospeak why creators say unalive",
]
PER_SEARCH = 20
RELEVANT = re.compile(r"\b(demonetis|demonetiz|monetis|monetiz|advertiser[- ]?friendly|"
                      r"yellow dollar|limited ads|ad[- ]?sense|guidelines|self[- ]?censor|"
                      r"algospeak|unalive|ad revenue|advertiser)\b", re.I)
FLAT = {"quiet": True, "skip_download": True, "no_warnings": True, "ignoreerrors": True,
        "extract_flat": True, "playlistend": 60}
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
    cands = []
    for q in QUERIES:
        try:
            ents = flat_ids(f"ytsearch{PER_SEARCH}:{q}")
            print(f"[search] {q!r} -> {len(ents)}", flush=True)
            cands += ents
        except Exception as e:
            print("search fail", q, str(e)[:50], flush=True)
    seen = set()
    for vid, title in cands:
        if not vid or vid in done or vid in seen: continue
        seen.add(vid)
        time.sleep(1.3)
        info = getinfo(vid)
        if not info: continue
        tx = captions(info)
        if not tx or len(tx.split()) < 150: continue
        if not RELEVANT.search((title or "") + " " + tx[:5000]):
            continue
        rec = {"id": vid, "type": "advice", "query": "advice-search",
               "channel": info.get("channel", ""), "upload_date": info.get("upload_date", ""),
               "title": title, "description": (info.get("description") or "")[:1500],
               "transcript": tx}
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n"); fh.flush(); kept += 1
        print(f"   advice kept {kept}: {title[:55]}", flush=True)
    fh.close()
    print(f"DONE. +{kept} advice transcripts -> {OUT}")


if __name__ == "__main__":
    main()
