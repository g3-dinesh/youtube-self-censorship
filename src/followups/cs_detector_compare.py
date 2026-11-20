"""#4 (supervisor) — detector PRECISION vs RECALL characterisation.

Two detectors are in play:
  STRICT  = bleeps + digit/letter masks + UNAMBIGUOUS coded terms (unalive, sewer
            slide, pdf file, seggs, le$bian, kys, grape, yahtzee...). High precision
            (hand-validated ~100%).
  LEXICON = the full 35-term discovered euphemism list, which also contains
            HIGH-FREQUENCY BENIGN words (corn, panini, panorama, mascara,
            accountant, swimmers, saltines, cornucopia...). High recall, LOW
            precision: any video merely SAYING 'corn' or 'accountant' is flagged.

This quantifies the precision cost of the broad lexicon per-term, and states
exactly why the project relies on the STRICT detector. True recall of STRICT
cannot be estimated without a human reference set (-> deliverable #2).

-> results_deliverable/casestudies/cs_detector_compare.csv
"""
import csv, json, os, re
from collections import Counter
import casestudy_common as C

lex = C.load_lexicon()
# terms whose plain meaning is common English (benign-prone) -> precision risk
BENIGN_PRONE = {"accountant", "corn", "corn addiction", "cornucopia", "mascara",
                "panini", "panorama", "panoramic", "saltines", "sa", "swimmers",
                "the vid", "the rona", "spicy accountant", "spicy eggplant",
                "cheese pizza", "grippy sock", "le dollar bean", "pew pew", "ouid"}
UNAMBIG = [(t, rx) for t, rx in lex if t not in BENIGN_PRONE]
BENIGN = [(t, rx) for t, rx in lex if t in BENIGN_PRONE]

MASTER = os.path.join(C.REPO, "data", "master_transcripts.jsonl")
n = 0
strict_hits = 0          # bleep/digitmask OR unambiguous coded term
lex_hits = 0             # any lexicon term (full)
benign_only_hits = 0     # flagged by lexicon ONLY via a benign-prone term
term_vidcount = Counter()
benign_term_vidcount = Counter()

for l in open(MASTER, encoding="utf-8"):
    try: d = json.loads(l)
    except Exception: continue
    t = d.get("transcript") or ""
    if len(t.split()) < 50:
        continue
    n += 1
    tl = t.lower()
    strict = bool(C.BLEEP.search(t) or C.DIGIT_MASK.search(t) or any(rx.search(tl) for _, rx in UNAMBIG))
    lexf = False
    hit_benign = False; hit_unambig = bool(C.BLEEP.search(t) or C.DIGIT_MASK.search(t) or any(rx.search(tl) for _, rx in UNAMBIG))
    for term, rx in lex:
        if rx.search(tl):
            lexf = True; term_vidcount[term] += 1
            if term in BENIGN_PRONE:
                hit_benign = True; benign_term_vidcount[term] += 1
    if strict: strict_hits += 1
    if lexf: lex_hits += 1
    if lexf and not hit_unambig and hit_benign:
        benign_only_hits += 1

rows = [
    ["videos scanned", n],
    ["STRICT detector flags (bleep/mask + unambiguous coded)", strict_hits, f"{100*strict_hits/n:.1f}%"],
    ["FULL LEXICON flags", lex_hits, f"{100*lex_hits/n:.1f}%"],
    ["flagged by LEXICON ONLY via a benign-prone word", benign_only_hits,
        f"{100*benign_only_hits/n:.1f}% of corpus = precision loss"],
    ["lexicon over-count factor (full/strict)", round(lex_hits / max(1, strict_hits), 1)],
    ["", "", ""],
    ["--- top benign-prone terms by videos flagged (likely FALSE positives) ---", "", ""],
]
for term, cnt in benign_term_vidcount.most_common(12):
    rows.append([f"   '{term}'", cnt, f"{100*cnt/n:.1f}% of videos"])
rows.append(["", "", ""])
rows.append(["--- unambiguous coded terms by videos flagged (true masking) ---", "", ""])
ut = Counter({t: term_vidcount[t] for t, _ in UNAMBIG})
for term, cnt in ut.most_common(12):
    if cnt:
        rows.append([f"   '{term}'", cnt, f"{100*cnt/n:.2f}%"])

out = os.path.join(C.CS, "cs_detector_compare.csv")
with open(out, "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh); w.writerow(["metric", "count", "note"])
    for r in rows:
        w.writerow(r + [""] * (3 - len(r)))
for r in rows:
    print("  " + " | ".join(str(x) for x in r))
print("-> saved", out)
