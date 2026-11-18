"""STAGE 4 (analysis) - Self-censorship over time.

Builds a dated quarterly timeline of how often creators self-censor (mask /
use algospeak), overall and by content category, using the shared masking
detector. Plots the trend with 95% Wilson confidence bands.

Reads a dated transcript corpus (one JSON object per line with upload_date,
category, transcript). The bundled data/euph_transcripts.jsonl (1,189 dated
videos across 21 categories) is the default.

CARE taken against a real confound: the mix of creators/categories changes over
time, so a raw pooled trend can move just because the *sample* changed, not
because behaviour did. This script therefore reports per-quarter sample size and
lets you read any category separately (--category) rather than trusting the
pooled line alone.

Input
  --corpus  JSONL of dated transcripts (default data/euph_transcripts.jsonl)
  --category  optional: restrict to one category (avoids the composition confound)
  --min-n   minimum videos per quarter to plot a point (default 5)

Output
  outputs/timeline_masking_by_quarter.csv
  outputs/fig_timeline.png

Example
  python src/09_timeline_analysis.py
  python src/09_timeline_analysis.py --category true-crime
"""
import argparse, csv, json, os
from collections import defaultdict
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import common as C


def main():
    ap = argparse.ArgumentParser(description="Stage 4: self-censorship timeline.")
    ap.add_argument("--corpus", default=os.path.join(C.REPO, "data", "euph_transcripts.jsonl"))
    ap.add_argument("--category", default="", help="restrict to one category")
    ap.add_argument("--min-n", type=int, default=5)
    args = ap.parse_args()

    per_q = defaultdict(lambda: [0, 0])          # quarter -> [masked, total]
    per_cat = defaultdict(int)
    for ln in open(args.corpus, encoding="utf-8"):
        ln = ln.strip()
        if not ln:
            continue
        try:
            r = json.loads(ln)
        except Exception:
            continue
        u = str(r.get("upload_date") or "")
        tx = r.get("transcript") or ""
        cat = r.get("category") or "uncategorised"
        if len(u) != 8 or not u.isdigit() or len(tx.split()) < 50:
            continue
        per_cat[cat] += 1
        if args.category and cat != args.category:
            continue
        q = C.quarter(u)
        per_q[q][1] += 1
        if C.masked(tx):
            per_q[q][0] += 1

    quarters = sorted(per_q)
    rows = []
    for q in quarters:
        k, nn = per_q[q]
        p, lo, hi = C.wilson(k, nn)
        rows.append({"quarter": q, "n_videos": nn, "n_masked": k,
                     "masking_rate_pct": p, "ci_lo": lo, "ci_hi": hi})
    out_csv = os.path.join(C.OUT, "timeline_masking_by_quarter.csv")
    with open(out_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["quarter", "n_videos", "n_masked",
                                           "masking_rate_pct", "ci_lo", "ci_hi"])
        w.writeheader(); w.writerows(rows)

    # plot only quarters with enough videos to be stable
    plot = [r for r in rows if r["n_videos"] >= args.min_n]
    xs = list(range(len(plot)))
    ys = [r["masking_rate_pct"] for r in plot]
    lo = [r["masking_rate_pct"] - r["ci_lo"] for r in plot]
    hi = [r["ci_hi"] - r["masking_rate_pct"] for r in plot]
    fig, ax = plt.subplots(figsize=(12, 5.5))
    ax.errorbar(xs, ys, yerr=[lo, hi], marker="o", lw=2, color=C.BLUE,
                ecolor=C.GRID, capsize=3)
    ax.set_xticks(xs); ax.set_xticklabels([r["quarter"] for r in plot], rotation=60, fontsize=7)
    ax.set_ylabel("% of videos with masking"); ax.set_ylim(0, 100)
    title = "Self-censorship over time" + (f" - {args.category}" if args.category else " (all categories pooled)")
    ax.set_title(f"{title}   (95% Wilson bands; points need n>={args.min_n})",
                 weight="bold", fontsize=12)
    # annotate per-quarter n so the composition confound is visible
    for x, r in zip(xs, plot):
        ax.annotate(str(r["n_videos"]), (x, 2), fontsize=6, ha="center", color="#888")
    ax.grid(axis="y", color=C.GRID); ax.set_axisbelow(True)
    fig.tight_layout(); fig.savefig(os.path.join(C.OUT, "fig_timeline.png"), dpi=140)

    print(f"corpus: {sum(v for v in per_cat.values())} dated videos, {len(per_cat)} categories")
    if not args.category:
        print("top categories:", dict(sorted(per_cat.items(), key=lambda x: -x[1])[:6]))
    print(f"quarters plotted (n>={args.min_n}): {len(plot)} of {len(rows)}")
    print(f"-> {out_csv}\n-> outputs/fig_timeline.png")


if __name__ == "__main__":
    main()
