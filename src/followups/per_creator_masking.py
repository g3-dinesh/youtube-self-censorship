"""Per-creator masking rate over the master corpus, using the shared strict
detector (bleeps + digit/letter masks + curated euphemism lexicon). Feeds the
heavy-vs-light masker selection for the creator-level Talk-vs-Walk test (#1b).

NOTE: the full euphemism lexicon includes benign-prone words (see
cs_detector_compare.py / Results_Exp4b); treat these broad rates as RECALL-heavy.
The validated high-precision rates are in data/experiments/self_censorship_by_creator.csv.

Input : data/master_transcripts.jsonl
Output: data/experiments/master_masking_by_creator.csv
"""
import json, os, csv
from collections import defaultdict
import casestudy_common as C

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
lex = C.load_lexicon()


def masks(t):
    tl = t.lower()
    return bool(C.BLEEP.search(t) or C.DIGIT_MASK.search(t) or any(rx.search(tl) for _, rx in lex))


def main():
    cnt = defaultdict(lambda: [0, 0])  # creator -> [masked, total]
    with open(os.path.join(REPO, "data", "master_transcripts.jsonl"), encoding="utf-8") as fh:
        for l in fh:
            try: d = json.loads(l)
            except Exception: continue
            t = d.get("transcript") or ""
            if len(t.split()) < 50:
                continue
            ch = d.get("channel", "?")
            cnt[ch][1] += 1; cnt[ch][0] += (1 if masks(t) else 0)
    rows = sorted(([ch, m, n, round(100 * m / n, 1)] for ch, (m, n) in cnt.items() if n >= 8),
                  key=lambda r: -r[3])
    out = os.path.join(REPO, "data", "experiments", "master_masking_by_creator.csv")
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(["creator", "masked", "total", "masked_pct_broad"])
        w.writerows(rows)
    for r in rows[:20]:
        print(f"  {r[0][:32]:32} {r[3]:5.1f}%  ({r[1]}/{r[2]})")
    print("-> saved", out)


if __name__ == "__main__":
    main()
