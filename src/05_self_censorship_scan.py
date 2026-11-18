"""STAGE 2 (signal) - Self-censorship / masking scanner.

Scans every transcript for masking (bleeps, letter-swaps) and curated algospeak
euphemisms, using the one shared detector in common.py. Also runs the "leaky
mask" test: does a video mask a word AND still say the plain word somewhere in
the same transcript? If so, the masking cannot be defeating YouTube's transcript
scanner - it is a stylistic reflex, not functional keyword evasion.

Input
  the bundled dataset (data/dataset/<creator>/*.json), no arguments needed

Output
  outputs/self_censorship_hits.csv   per-video: masked?, mask_count, euphemisms
  outputs/self_censorship_summary.csv  totals + leak rate
  outputs/fig_self_censorship.png

Example
  python src/05_self_censorship_scan.py
"""
import csv, os, re
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import common as C

# plain-word forms, to test whether a masked video "leaks" the real word
PLAIN = re.compile(r"\b(?:shit|fuck(?:ing|ed|er)?|bitch|kill(?:ed|ing|s)?|"
                   r"murder(?:ed|s)?|suicide|rape(?:d|s|ist)?)\b", re.I)


def main():
    lex = C.load_lexicon()
    rows = []
    n = masked_n = leaky_n = 0
    for v in C.load_videos():
        n += 1
        tx = v["transcript"]; low = tx.lower()
        euph = sorted({t for t, rx in lex if rx.search(low)})
        is_masked = v["masked"] or bool(euph)
        leaks = bool(PLAIN.search(low))
        if is_masked:
            masked_n += 1
            if leaks:
                leaky_n += 1
        rows.append({"video_id": v["id"], "channel": v["slug"], "date": v["date"],
                     "masked": int(is_masked), "mask_count": v["mask_count"],
                     "euphemisms": "|".join(euph), "leaks_plain_word": int(leaks)})

    # per-video hits
    with open(os.path.join(C.OUT, "self_censorship_hits.csv"), "w", newline="",
              encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

    leak_rate = C.pct(leaky_n, masked_n)
    summary = [
        ["videos_scanned", n],
        ["videos_with_masking", masked_n],
        ["masking_rate_pct", C.pct(masked_n, n)],
        ["of_masked_videos_that_ALSO_say_plain_word", leaky_n],
        ["leak_rate_pct", leak_rate],
    ]
    with open(os.path.join(C.OUT, "self_censorship_summary.csv"), "w", newline="",
              encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(["metric", "value"]); w.writerows(summary)

    # chart: the leaky-mask result
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.bar(["consistent\n(masked only)", "LEAKY\n(masked + plain word)"],
           [100 - leak_rate, leak_rate], color=[C.GREEN, C.VERM], width=0.55)
    for i, val in enumerate([100 - leak_rate, leak_rate]):
        ax.text(i, val + 1, f"{val:.0f}%", ha="center", fontsize=14, weight="bold")
    ax.set_ylim(0, 100); ax.set_ylabel("% of masking videos")
    ax.set_title("Masking 'leaks': the same video also says the plain word",
                 weight="bold", fontsize=11)
    ax.grid(axis="y", color=C.GRID); ax.set_axisbelow(True)
    fig.tight_layout(); fig.savefig(os.path.join(C.OUT, "fig_self_censorship.png"), dpi=150)

    for k, val in summary:
        print(f"  {k:48s} {val}")
    print(f"\n-> outputs/self_censorship_hits.csv, self_censorship_summary.csv, fig_self_censorship.png")


if __name__ == "__main__":
    main()
