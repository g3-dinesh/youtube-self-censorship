"""#1 (creator-level): find each BEHAVIOURAL creator's OWN demonetisation talk-video.

For creators we already have a masking rate for (self_censorship_by_creator.csv),
search YouTube for a video BY THAT CREATOR about demonetisation/monetisation, grab
the caption. Later we folk-score it (Talk) and pair with their masking rate (Walk)
-> a within-creator Talk-vs-Walk comparison.

Keeps only videos whose uploader matches the creator (substring match on channel)
AND which discuss demonetisation, >=120 words. -> data/creator_talk.jsonl
"""
import json, os, re, time, urllib.request, urllib.error
import yt_dlp

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "creator_talk.jsonl")
# handle -> (readable search name, list of channel-name substrings to accept)
CREATORS = {
    "coryxkenshin":   ("CoryxKenshin",     ["coryxkenshin"]),
    "crowder":        ("Steven Crowder",   ["crowder", "louder with crowder"]),
    "doctormike":     ("Doctor Mike",      ["doctor mike"]),
    "thatchapter":    ("That Chapter",     ["that chapter"]),
    "baileysarian":   ("Bailey Sarian",    ["bailey sarian"]),
    "defranco":       ("Philip DeFranco",  ["defranco", "philip defranco"]),
    "kulinski":       ("Kyle Kulinski",    ["kulinski", "secular talk"]),
    "palebluethoughts":("Pale Blue Thoughts",["pale blue"]),
    "timpool":        ("Tim Pool",         ["tim pool", "timcast"]),
    "kurtisconner":   ("Kurtis Conner",    ["kurtis conner"]),
    "shamsharma":     ("Sham Sharma",      ["sham sharma"]),
    "pakman":         ("David Pakman",     ["pakman"]),
    "tyt":            ("The Young Turks",  ["young turks", "tyt"]),
}
TERMS = ["demonetized", "demonetization", "monetization youtube", "advertiser friendly", "age restricted"]
DEMON = re.compile(r"\b(demonetis|demonetiz|monetis|monetiz|yellow dollar|limited ads|"
                   r"adsense|advertiser|ad revenue|age[- ]?restrict|strike|guidelines|"
                   r"algorithm|censor)\b", re.I)
FLAT = {"quiet": True, "skip_download": True, "no_warnings": True, "ignoreerrors": True,
        "extract_flat": True, "playlistend": 8}
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
            try:
                raw = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=25).read().decode("utf-8", "replace")
                d = json.loads(raw)
                return re.sub(r"\s+", " ", "".join(s.get("utf8", "") for ev in d.get("events", []) for s in ev.get("segs") or [])).strip()
            except Exception:
                break
    return ""


def search(q, n=8):
    with yt_dlp.YoutubeDL(FLAT) as y:
        info = y.extract_info(f"ytsearch{n}:{q}", download=False)
    return [(e.get("id"), e.get("title", ""), (e.get("channel") or e.get("uploader") or "")) for e in (info.get("entries") or []) if e and e.get("id")]


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
            try: done.add(json.loads(l)["handle"])
            except: pass
    fh = open(OUT, "a", encoding="utf-8")
    for handle, (name, subs) in CREATORS.items():
        if handle in done:
            print(f"[{handle}] already done", flush=True); continue
        got = False
        for term in TERMS:
            if got: break
            try:
                hits = search(f"{name} {term}")
            except Exception as e:
                print(f"[{handle}] search err {str(e)[:40]}", flush=True); continue
            for vid, title, chan in hits:
                chl = (chan or "").lower()
                if not any(s in chl for s in subs):
                    continue  # must be uploaded BY the creator
                time.sleep(1.2)
                info = getinfo(vid)
                if not info: continue
                # double-check channel from full info
                fch = (info.get("channel") or "").lower()
                if not any(s in fch for s in subs): continue
                tx = captions(info)
                if not tx or len(tx.split()) < 120: continue
                if not DEMON.search(title + " " + tx[:4000]): continue
                rec = {"handle": handle, "name": name, "id": vid, "type": "creator_talk",
                       "channel": info.get("channel", ""), "title": title,
                       "upload_date": info.get("upload_date", ""), "transcript": tx}
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n"); fh.flush()
                print(f"[{handle}] GOT: {title[:55]}", flush=True)
                got = True; break
        if not got:
            print(f"[{handle}] no own demon video found", flush=True)
    fh.close()
    print("DONE ->", OUT)


if __name__ == "__main__":
    main()
