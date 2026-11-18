"""STAGE 4 (analysis) - Counterfactual: does algospeak actually help?

The flagship controlled experiment. We took 60 sensitive clips and made THREE
versions of each: (A) original, (B) with algospeak substituted in
(rape->grape, kill->unalive, ...), (C) algospeak + a disclaimer. The same two
judges (System A official policy, System B folk belief) rated all three. Because
only the wording changes, any difference in verdict is caused by the wording.

Finding: algospeak does NOT make the policy judge more lenient - it slightly
BACKFIRES (A: 47% -> 57% not-monetised). A disclaimer is what actually helps
(->23%). The folk-belief judge stays scared (~90%) no matter what. So the ritual
is aimed at the wrong lever.

Input (bundled, precomputed judge output)
  data/counterfactual_judge_output.jsonl   seg_id, version, A_verdict, B_verdict

Output
  outputs/counterfactual_results.csv
  outputs/fig_counterfactual.png

Example
  python src/10_counterfactual_experiment.py
"""
import csv, json, os
from collections import defaultdict
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import common as C

CF = os.path.join(C.REPO, "data", "counterfactual_judge_output.jsonl")
VERS = ["A_original", "B_euphemised", "C_euph_disclaimer"]
LAB = {"A_original": "original", "B_euphemised": "+ algospeak",
       "C_euph_disclaimer": "+ algospeak\n+ disclaimer"}


def main():
    rows = [json.loads(l) for l in open(CF, encoding="utf-8") if l.strip()]
    byseg = defaultdict(dict)
    for r in rows:
        byseg[r["seg_id"]][r["version"]] = r

    def not_monetised(ver, sysn):
        vals = [byseg[s][ver][f"{sysn}_verdict"] for s in byseg if ver in byseg[s]]
        n = len(vals)
        k = sum(1 for v in vals if v in ("demonetise", "limited"))
        p, lo, hi = C.wilson(k, n)
        return p, lo, hi, n

    out = []
    for sysn, name in (("A", "System A (real policy)"), ("B", "System B (folk belief)")):
        for ver in VERS:
            p, lo, hi, n = not_monetised(ver, sysn)
            out.append({"system": name, "version": ver, "pct_not_monetised": p,
                        "ci_lo": lo, "ci_hi": hi, "n": n})
    with open(os.path.join(C.OUT, "counterfactual_results.csv"), "w", newline="",
              encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["system", "version", "pct_not_monetised",
                                           "ci_lo", "ci_hi", "n"])
        w.writeheader(); w.writerows(out)

    fig, ax = plt.subplots(figsize=(10, 5.8))
    x = range(len(VERS)); wd = 0.38
    for off, sysn, col, lab in [(-wd / 2, "A", C.BLUE, "System A - real policy"),
                                (wd / 2, "B", C.VERM, "System B - creator folk-belief")]:
        ys, los, his = [], [], []
        for ver in VERS:
            p, lo, hi, n = not_monetised(ver, sysn)
            ys.append(p); los.append(p - lo); his.append(hi - p)
        ax.bar([i + off for i in x], ys, wd, color=col, label=lab,
               yerr=[los, his], capsize=4, ecolor="#555")
        for i, v in zip(x, ys):
            ax.text(i + off, v + 2, f"{v:.0f}%", ha="center", fontsize=11, weight="bold")
    ax.set_xticks(list(x)); ax.set_xticklabels([LAB[v] for v in VERS], fontsize=10)
    ax.set_ylim(0, 100); ax.set_ylabel("% judged NOT fully monetised")
    ax.set_title("Algospeak doesn't fool the policy and can't calm the fear\n"
                 "Controlled counterfactual: same 60 clips, 3 versions", weight="bold", fontsize=12.5)
    ax.legend(frameon=False, fontsize=10, loc="upper right")
    ax.grid(axis="y", color=C.GRID); ax.set_axisbelow(True)
    fig.tight_layout(); fig.savefig(os.path.join(C.OUT, "fig_counterfactual.png"), dpi=150)

    print("System A (real policy) not-monetised:", [f"{not_monetised(v, 'A')[0]}%" for v in VERS])
    print("System B (folk belief) not-monetised:", [f"{not_monetised(v, 'B')[0]}%" for v in VERS])
    print("-> outputs/counterfactual_results.csv, fig_counterfactual.png")


if __name__ == "__main__":
    main()
