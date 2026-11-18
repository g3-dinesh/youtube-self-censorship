import argparse
import csv
import glob
import json
import os
import re
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(HERE, "..", "data", "dataset")
DEFAULT_OUT = os.path.join(HERE, "..", "data", "experiments",
                           "self_censorship.csv")
DEFAULT_BY_CREATOR = os.path.join(HERE, "..", "data", "experiments",
                                  "self_censorship_by_creator.csv")

ALGOSPEAK = {
    "unalive": "kill/suicide",
    "unalived": "killed",
    "unaliving": "killing",
    "sewer slide": "suicide",
    "seweredside": "suicide",
    "self delete": "suicide",
    "self-delete": "suicide",
    "kys": "kill yourself",
    "seggs": "sex",
    "seggsual": "sexual",
    "le dollar bean": "lesbian",
    "le$bian": "lesbian",
    "leg booty": "lgbt",
    "cornucopia": "porn",
    "corn star": "porn star",
    "spicy accountant": "sex worker",
    "accountant": "sex worker",
    "panini": "pandemic",
    "panorama": "pandemic",
    "camping": "abortion",
    "the vid": "covid",
    "the rona": "covid",
    "nip nops": "nipples",
    "pew pew": "gun",
    "pewpew": "gun",
    "pdf file": "pedophile",
    "pdf files": "pedophiles",
    "sewerslide": "suicide",
    "mascara": "sexual assault",
    "grippy sock": "psychiatric ward",
    "grippy socks": "psychiatric ward",
    "cheese pizza": "child abuse material",
    "dream": "death",
    "nsfw": "explicit",
    "p*rn": "porn",
    "s*x": "sex",
    "s3x": "sex",
    "r*pe": "rape",
    "gr@pe": "rape",
    "grape": "rape",
    "k*ll": "kill",
    "k1ll": "kill",
    "d*e": "die",
    "di*": "die",
    "su*cide": "suicide",
    "suicid3": "suicide",
    "t*rror": "terror",
    "n*zi": "nazi",
    "g*n": "gun",
    "sh**ting": "shooting",
    "sh00ting": "shooting",
    "genocide": None,
    "yt": "youtube",
}

MASK_RE = re.compile(r"\b[a-z]{1,}[\*#][a-z\*#]{0,}[a-z]\b", re.I)
NUMERIC_LEET_RE = re.compile(r"\b[a-z]*[013457][a-z]+\b", re.I)

META_PHRASES = [
    "youtube won't let me", "youtube wont let me", "youtube won't let us",
    "youtube wont let us", "not allowed to say on youtube", "for the algorithm",
    "feed the algorithm", "get demonetized", "get demonetised",
    "so i don't get demonetiz", "so i dont get demonetiz", "so we don't get demonetiz",
    "so we dont get demonetiz", "get age restricted", "get age-restricted",
    "rhymes with", "the s word", "the k word", "the r word", "the n word",
    "i have to censor", "have to bleep", "gonna get flagged", "gonna get bleeped",
    "keep this monetized", "keep this monetised", "keep it monetized",
    "keep it monetised", "advertiser friendly", "advertiser-friendly",
    "ad friendly", "ad-friendly", "censor myself", "censor ourselves",
    "not gonna say the word", "can't even say", "cant even say",
]

STOPWORDS = {"yt", "accountant", "grape", "genocide", "camping", "mascara",
             "dream", "nsfw", "cornucopia", "panorama"}


def scan(text):
    low = " ".join((text or "").lower().split())
    algo = Counter()
    for term in ALGOSPEAK:
        c = len(re.findall(r"\b" + re.escape(term) + r"\b", low))
        if c:
            algo[term] += c
    meta = Counter()
    for phrase in META_PHRASES:
        c = len(re.findall(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", low))
        if c:
            meta[phrase] += c
    masks = len(MASK_RE.findall(text or ""))
    return algo, meta, masks


def snippet(text, term, width=80):
    low = (text or "").lower()
    i = low.find(term)
    if i < 0:
        return ""
    a = max(0, i - width)
    b = min(len(text), i + len(term) + width)
    return re.sub(r"\s+", " ", text[a:b]).strip()


def main():
    ap = argparse.ArgumentParser(
        description="Detect on-screen self-censorship: creators swapping words to "
                    "dodge demonetisation (algospeak like 'unalive', 'seggs', "
                    "'sewer slide'), masked spellings (k*ll, s3x), and explicit "
                    "meta-talk ('YouTube won't let me say', 'for the algorithm'). "
                    "Scores every transcript and aggregates per creator. This is "
                    "the self-censorship proof-of-concept signal.")
    ap.add_argument("--dataset", default=DATASET_DIR)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--by-creator", default=DEFAULT_BY_CREATOR)
    ap.add_argument("--min-hits", type=int, default=1,
                    help="only keep videos with at least this many total signals")
    args = ap.parse_args()

    files = glob.glob(os.path.join(args.dataset, "*", "*.json"))
    rows = []
    per_creator = {}
    scanned = 0
    for path in files:
        try:
            rec = json.load(open(path, encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(rec, dict) or not rec.get("id"):
            continue
        transcript = rec.get("transcript") or ""
        if not transcript.strip():
            continue
        scanned += 1
        algo, meta, masks = scan(transcript)
        algo_kept = {k: v for k, v in algo.items() if k not in STOPWORDS}
        n_algo = sum(algo_kept.values())
        n_meta = sum(meta.values())
        total = n_algo + n_meta + masks
        creator = rec.get("slug", "")
        c = per_creator.setdefault(creator, {"videos": 0, "flagged": 0,
                                             "algo": 0, "meta": 0, "masks": 0})
        c["videos"] += 1
        if total >= args.min_hits:
            c["flagged"] += 1
            c["algo"] += n_algo
            c["meta"] += n_meta
            c["masks"] += masks
            ev_term = (next(iter(algo_kept)) if algo_kept
                       else next(iter(meta)) if meta else "")
            rows.append({
                "video_id": rec.get("id"),
                "creator": creator,
                "title": (rec.get("title") or "")[:100],
                "url": rec.get("url", ""),
                "total_signals": total,
                "algospeak_hits": n_algo,
                "meta_phrase_hits": n_meta,
                "masked_words": masks,
                "algospeak_terms": "|".join(f"{k}:{v}" for k, v in
                                            sorted(algo_kept.items())),
                "meta_phrases": "|".join(sorted(meta)),
                "evidence": snippet(transcript, ev_term) if ev_term else "",
            })

    rows.sort(key=lambda r: r["total_signals"], reverse=True)
    fields = ["video_id", "creator", "title", "url", "total_signals",
              "algospeak_hits", "meta_phrase_hits", "masked_words",
              "algospeak_terms", "meta_phrases", "evidence"]
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    cfields = ["creator", "videos", "flagged", "flagged_pct", "algospeak_hits",
               "meta_phrase_hits", "masked_words"]
    with open(args.by_creator, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cfields)
        w.writeheader()
        for creator, c in sorted(per_creator.items(),
                                 key=lambda kv: -kv[1]["flagged"]):
            w.writerow({
                "creator": creator, "videos": c["videos"],
                "flagged": c["flagged"],
                "flagged_pct": round(100.0 * c["flagged"] / c["videos"], 1)
                if c["videos"] else 0,
                "algospeak_hits": c["algo"], "meta_phrase_hits": c["meta"],
                "masked_words": c["masks"],
            })

    print(f"scanned {scanned} transcripts")
    print(f"videos with self-censorship signals: {len(rows)}")
    print(f"-> {args.out}")
    print(f"-> {args.by_creator}")
    print("\nper-creator (flagged / videos):")
    for creator, c in sorted(per_creator.items(),
                             key=lambda kv: -kv[1]["flagged"]):
        if c["flagged"]:
            print(f"  {creator:14} {c['flagged']:3}/{c['videos']:<4} "
                  f"algospeak={c['algo']} meta={c['meta']} masks={c['masks']}")
    print("\ntop 15 videos:")
    for r in rows[:15]:
        print(f"  [{r['total_signals']:2}] {r['video_id']:14} {r['creator']:10} "
              f"{r['algospeak_terms'][:50]}")


if __name__ == "__main__":
    main()
