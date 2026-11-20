"""#3 (supervisor) — leaky-mask PROXIMITY. When a creator masks a concept AND
also says the plain word in the same video, HOW CLOSE are they?

For each masked-concept token, find the nearest PLAIN token of the same concept
and record the gap in words. Proxy: speech ~2.5 words/sec, so 75 words ~= 30s.
Classify each masked token:
  immediate  : plain word within 12 words (same breath / emphatic repetition)
  same_sent  : plain word in the same sentence
  within_30s : plain word within 75 words
Distinguishes habitual performance (plain word right next to the mask) from
deliberate context-dependent censorship (mask isolated, plain far away/elsewhere).
-> results_deliverable/casestudies/cs_leaky_proximity.csv
"""
import csv, glob, json, os, re, statistics
import casestudy_common as C

CONC = {
    "profanity": (re.compile(r"\b(?:sh[1!]t|f[4@]ck|f+ck|b[1!]tch|btch|ph[u4]ck)\b", re.I),
                  re.compile(r"\b(?:shit|fuck(?:ing|ed|er)?|bitch)\b", re.I)),
    "kill/suicide": (re.compile(r"\bunaliv\w*", re.I),
                     re.compile(r"\b(?:kill(?:ed|ing|s)?|murder(?:ed|s)?|suicide|died)\b", re.I)),
    "rape": (re.compile(r"(?<![a-z])grape(?![a-z])", re.I),
             re.compile(r"\brape(?:d|s|ist)?\b", re.I)),
}
IMMEDIATE, SAMESENT, W30 = 12, None, 75

gaps = []            # word-gap to nearest plain, per masked token (that has any plain in video)
n_masked_tok = 0     # masked tokens total (concept masked)
n_with_plain = 0     # masked tokens that have >=1 plain of same concept somewhere in video
cls = {"immediate": 0, "same_sentence": 0, "within_30s": 0, "far_or_elsewhere": 0}
vids = 0


def word_positions(tokens, rx):
    return [i for i, w in enumerate(tokens) if rx.search(w)]


def sentence_index(text):
    # map word index -> sentence id
    sid = []; s = 0
    for tok in text.split():
        sid.append(s)
        if tok.endswith((".", "!", "?")):
            s += 1
    return sid


MASTER = os.path.join(os.path.dirname(C.DATASET), "master_transcripts.jsonl")
def iter_videos():
    if os.path.exists(MASTER):
        for l in open(MASTER, encoding="utf-8"):
            try: yield json.loads(l)
            except Exception: continue
    else:
        for f in glob.glob(os.path.join(C.DATASET, "*", "*.json")):
            try: yield json.load(open(f, encoding="utf-8"))
            except Exception: continue

for d in iter_videos():
    t = d.get("transcript") or ""
    toks = t.split()
    if len(toks) < 50:
        continue
    low_toks = [w.lower() for w in toks]
    sid = sentence_index(t)
    used = False
    for name, (cr, pr) in CONC.items():
        mpos = word_positions(low_toks, cr)
        ppos = word_positions(low_toks, pr)
        if not mpos:
            continue
        n_masked_tok += len(mpos)
        if not ppos:
            continue
        pset = ppos
        for mi in mpos:
            n_with_plain += 1
            nearest = min(pset, key=lambda pi: abs(pi - mi))
            gap = abs(nearest - mi)
            gaps.append(gap)
            same_sent = (0 <= nearest < len(sid) and 0 <= mi < len(sid) and sid[mi] == sid[nearest])
            if gap <= IMMEDIATE:
                cls["immediate"] += 1
            elif same_sent:
                cls["same_sentence"] += 1
            elif gap <= W30:
                cls["within_30s"] += 1
            else:
                cls["far_or_elsewhere"] += 1
            used = True
    if used:
        vids += 1


def pct(a, b):
    return round(100 * a / b, 1) if b else 0.0


rows = [
    ["videos contributing masked+plain concept pairs", vids],
    ["masked concept tokens (any)", n_masked_tok],
    ["masked tokens with >=1 plain of same concept in video", n_with_plain,
        f"{pct(n_with_plain, n_masked_tok)}% of masked tokens 'leak'"],
    ["", ""],
    ["median word-gap mask->nearest plain", (statistics.median(gaps) if gaps else None)],
    ["mean word-gap", (round(statistics.mean(gaps), 1) if gaps else None)],
    ["", ""],
    ["IMMEDIATE (plain within 12 words / same breath)", cls["immediate"], f"{pct(cls['immediate'], n_with_plain)}%"],
    ["SAME SENTENCE", cls["same_sentence"], f"{pct(cls['same_sentence'], n_with_plain)}%"],
    ["WITHIN ~30s (<=75 words)", cls["within_30s"], f"{pct(cls['within_30s'], n_with_plain)}%"],
    ["FAR / elsewhere in video (>75 words)", cls["far_or_elsewhere"], f"{pct(cls['far_or_elsewhere'], n_with_plain)}%"],
]
near = cls["immediate"] + cls["same_sentence"] + cls["within_30s"]
rows.append(["", ""])
rows.append(["TOTAL within ~30s or same sentence", near, f"{pct(near, n_with_plain)}% of leaks are LOCAL"])

out = os.path.join(C.CS, "cs_leaky_proximity.csv")
with open(out, "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh); w.writerow(["metric", "value", "note"])
    for r in rows:
        w.writerow(r + [""] * (3 - len(r)))
for r in rows:
    print("  " + " | ".join(str(x) for x in r))
print("-> saved", out)
