"""STAGE 3 (analysis) - Which policy are creators trying to avoid?

Combines three signals on the same videos: System A (official policy), System B
(creator folk belief), and ACTUAL ad-serving (has_player_ads; an ad present
PROVES monetisation - the one-directional rule). It then asks: among videos that
are literally serving ads (proven monetised), what fraction does folk belief
wrongly flag as "would be demonetised", versus the written policy? And do
creators MASK in those already-monetised videos (wasted self-censorship)?

This quantifies the headline: self-censorship is MISDIRECTED - aimed at a rule
creators believe in but that the policy (and the ad server) does not enforce.

Input (bundled, precomputed so this runs instantly for the demo)
  data/05_1000videos_ad_systemA_systemB.csv   video_id, systemA_verdict,
      systemB_verdict, has_player_ads
  data/ground_truth_labels.csv                creator-confirmed labels
  data/dataset/<creator>/*.json               for masking

Output
  outputs/policy_avoidance.csv
  outputs/fig_policy_avoidance.png

Example
  python src/08_policy_avoidance.py
"""
import csv, glob, json, os
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import common as C

AB_CSV = os.path.join(C.REPO, "data", "05_1000videos_ad_systemA_systemB.csv")
LABELS = os.path.join(C.REPO, "data", "ground_truth_labels.csv")


def is_demon(v):
    return v.strip().lower() in ("demonetise", "demonetize", "no ads", "no_ads", "limited")


def main():
    # transcripts by id, for the masking check
    tx = {}
    for f in glob.glob(os.path.join(C.DATASET, "*", "*.json")):
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        if d.get("id"):
            tx[d["id"]] = d.get("transcript") or ""

    rows = list(csv.DictReader(open(AB_CSV, encoding="utf-8-sig")))
    for x in rows:
        x["A_dem"] = is_demon(x["systemA_verdict"])
        x["B_dem"] = is_demon(x["systemB_verdict"])
        x["ads"] = x["has_player_ads"] == "1"
        x["masked"] = C.masked(tx.get(x["video_id"], ""))

    ads = [x for x in rows if x["ads"]]          # proven monetised
    na = len(ads)
    A_flag = sum(x["A_dem"] for x in ads)
    B_flag = sum(x["B_dem"] for x in ads)
    masked_mon = sum(x["masked"] for x in ads)

    gold = {r["video_id"]: r["label"] for r in csv.DictReader(open(LABELS, encoding="utf-8-sig"))}
    gm = [x for x in rows if gold.get(x["video_id"]) == "monetised"]
    gm_Bflag = sum(x["B_dem"] for x in gm)

    out = [
        ["videos_total", len(rows)],
        ["proven_monetised_ads_present", na],
        ["A_policy_flags_demonetise_on_monetised_pct", C.pct(A_flag, na)],
        ["B_folk_flags_demonetise_on_monetised_pct", C.pct(B_flag, na)],
        ["monetised_videos_creator_masked_pct", C.pct(masked_mon, na)],
        ["gold_creator_confirmed_monetised_n", len(gm)],
        ["of_gold_monetised_B_folk_flags_demonetise_pct", C.pct(gm_Bflag, len(gm)) if gm else "na"],
    ]
    with open(os.path.join(C.OUT, "policy_avoidance.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(["metric", "value"]); w.writerows(out)

    fig, ax = plt.subplots(figsize=(8, 5.5))
    vals = [C.pct(A_flag, na), C.pct(B_flag, na)]
    ax.bar(["Actual policy\n(System A)", "Creator belief\n(System B)"], vals,
           color=[C.BLUE, C.VERM], width=0.55)
    for i, v in enumerate(vals):
        ax.text(i, v + 2, f"{v:.0f}%", ha="center", fontsize=20, weight="bold")
    ax.set_ylim(0, 100); ax.set_ylabel("% of these videos judged 'would be demonetised'")
    ax.set_title(f"Creators fear demonetisation on videos that ARE serving ads\n"
                 f"(n={na} proven-monetised videos)", weight="bold", fontsize=12)
    ax.grid(axis="y", color=C.GRID); ax.set_axisbelow(True)
    fig.tight_layout(); fig.savefig(os.path.join(C.OUT, "fig_policy_avoidance.png"), dpi=150)

    for k, v in out:
        print(f"  {k:52s} {v}")
    print("\n-> outputs/policy_avoidance.csv, fig_policy_avoidance.png")


if __name__ == "__main__":
    main()
