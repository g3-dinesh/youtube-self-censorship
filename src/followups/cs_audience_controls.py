"""#5 (supervisor) — does audience 'mirroring' survive controls?

Bivariate claim: audiences use algospeak more when the creator masks
(41% vs 23%). Is that just creator/topic confounding? Two defences:

 (1) Creator fixed-effects LOGISTIC REGRESSION:
       aud_algospeak(video) ~ creator_masks + log(n_comments)
                              + sensitive_density + log(words) + C(creator)
     Report the creator_masks odds ratio with its 95% CI (the within-creator,
     topic-adjusted effect).
 (2) WITHIN-CREATOR paired test: for creators who have BOTH masked and
     non-masked videos, compare their audience-algospeak rate on masked vs
     non-masked videos, paired by creator (Wilcoxon). This removes the creator
     confound entirely by design.

-> results_deliverable/casestudies/cs_audience_controls.csv
"""
import csv, glob, json, os, re, math
import numpy as np
from collections import defaultdict
from scipy import stats
from sklearn.linear_model import LogisticRegression
import casestudy_common as C

lex = C.load_lexicon()
EXPLICIT = re.compile(r"\b(kill\w*|murder\w*|death|dead|suicide|rape\w*|sex\w*|drug\w*|"
                      r"gun\w*|shoot\w*|nazi|terror\w*|porn\w*)\b", re.I)


def comment_algospeak(t):
    tl = t.lower()
    if C.DIGIT_MASK.search(t) or C.BLEEP.search(t):
        return True
    return any(rx.search(tl) for _term, rx in lex)


def transcript_masks(t):
    tl = t.lower()
    return bool(C.BLEEP.search(t) or C.DIGIT_MASK.search(t) or any(rx.search(tl) for _term, rx in lex))


rows = []
for f in glob.glob(os.path.join(C.DATASET, "*", "*.json")):
    try:
        d = json.load(open(f, encoding="utf-8"))
    except Exception:
        continue
    coms = d.get("comments") or []
    if len(coms) < 10:
        continue
    t = d.get("transcript") or ""
    w = max(1, len(t.split()))
    texts = [(c.get("text") if isinstance(c, dict) else str(c)) or "" for c in coms]
    n = len(texts)
    algo = sum(1 for x in texts if comment_algospeak(x))
    rows.append({
        "creator": os.path.basename(os.path.dirname(f)),
        "aud_algo_any": 1 if algo > 0 else 0,
        "aud_algo_rate": algo / n,
        "creator_masks": 1 if transcript_masks(t) else 0,
        "log_ncom": math.log(n),
        "sens_density": 100.0 * len(EXPLICIT.findall(t)) / w,
        "log_words": math.log(w),
    })

n_vid = len(rows)
creators = sorted({r["creator"] for r in rows})

# ---------- bivariate (the original claim) ----------
m = [r for r in rows if r["creator_masks"]]
nm = [r for r in rows if not r["creator_masks"]]
biv_m = 100 * sum(r["aud_algo_any"] for r in m) / len(m)
biv_nm = 100 * sum(r["aud_algo_any"] for r in nm) / len(nm)

# ---------- (1) creator fixed-effects logistic regression ----------
cidx = {c: i for i, c in enumerate(creators)}
X = []; y = []
for r in rows:
    fe = [0] * len(creators); fe[cidx[r["creator"]]] = 1
    X.append([r["creator_masks"], r["log_ncom"], r["sens_density"], r["log_words"]] + fe[1:])
    y.append(r["aud_algo_any"])
X = np.array(X, float); y = np.array(y)
clf = LogisticRegression(max_iter=4000, C=1e6, solver="lbfgs")
clf.fit(X, y)
beta = clf.coef_[0][0]
# bootstrap CI on the creator_masks coefficient
rng = np.random.default_rng(11); betas = []
for _ in range(400):
    idx = rng.integers(0, len(y), len(y))
    try:
        c2 = LogisticRegression(max_iter=2000, C=1e6, solver="lbfgs").fit(X[idx], y[idx])
        betas.append(c2.coef_[0][0])
    except Exception:
        pass
lo, hi = np.percentile(betas, [2.5, 97.5]) if betas else (float("nan"), float("nan"))
OR, ORlo, ORhi = math.exp(beta), math.exp(lo), math.exp(hi)

# ---------- (2) within-creator paired ----------
bycre = defaultdict(lambda: {"m": [], "nm": []})
for r in rows:
    bycre[r["creator"]]["m" if r["creator_masks"] else "nm"].append(r["aud_algo_any"])
paired = []
for c, g in bycre.items():
    if g["m"] and g["nm"]:
        paired.append((c, 100 * sum(g["m"]) / len(g["m"]), 100 * sum(g["nm"]) / len(g["nm"])))
diffs = [mm - nn for _, mm, nn in paired]
if len(diffs) >= 2:
    try: wstat, wp = stats.wilcoxon(diffs)
    except Exception: wstat, wp = float("nan"), float("nan")
    mean_within = sum(diffs) / len(diffs)
    n_pos = sum(1 for dd in diffs if dd > 0)
else:
    wstat = wp = mean_within = n_pos = float("nan")

out_rows = [
    ["videos analysed (>=10 comments)", n_vid],
    ["creators", len(creators)],
    ["", ""],
    ["--- BIVARIATE (original claim) ---", ""],
    ["aud algospeak rate | creator MASKS", f"{biv_m:.1f}%  (n={len(m)})"],
    ["aud algospeak rate | creator does NOT mask", f"{biv_nm:.1f}%  (n={len(nm)})"],
    ["", ""],
    ["--- (1) CREATOR FIXED-EFFECTS LOGIT (topic+size adjusted) ---", ""],
    ["creator_masks odds ratio", f"{OR:.2f}"],
    ["  95% bootstrap CI", f"[{ORlo:.2f}, {ORhi:.2f}]"],
    ["  interpretation", "OR>1 & CI excludes 1 => mirroring survives controls"],
    ["", ""],
    ["--- (2) WITHIN-CREATOR PAIRED ---", ""],
    ["creators with BOTH masked & unmasked videos", len(paired)],
    ["mean within-creator diff (masked - unmasked) pp", (round(mean_within, 1) if paired else None)],
    ["creators where masked videos have MORE aud algospeak", f"{n_pos}/{len(paired)}"],
    ["Wilcoxon p", (round(wp, 4) if paired else None)],
]
out = os.path.join(C.CS, "cs_audience_controls.csv")
with open(out, "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh); w.writerow(["metric", "value"]); w.writerows(out_rows)
for r in out_rows:
    print("  " + " | ".join(str(x) for x in r))
print("-> saved", out)
