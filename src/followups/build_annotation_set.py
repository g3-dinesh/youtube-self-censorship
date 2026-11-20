"""#2 (supervisor) — build the HUMAN-VALIDATION instrument for the A-vs-B gap.

Produces a 200-video stratified sample for TWO independent human annotators, so
the project can report measurement validity (Cohen's kappa) and compare human
judgement against System A (policy) and System B (folk).

Outputs (results_deliverable/annotation/):
  annotation_sample.csv  -> given to annotators. Columns: id, url, title,
       transcript_excerpt, GUIDELINES, and BLANK a1_policy / a1_folk /
       a2_policy / a2_folk columns. NO machine verdicts shown.
  annotation_key.csv     -> held back. id + systemA_verdict + systemB_verdict +
       has_player_ads (ground-truth monetisation) + A_B_agreement.
  ANNOTATION_GUIDE.txt   -> the labelling protocol for annotators.

Sampling: stratified by (A_B_agreement x has_player_ads), oversampling the
A!=B disagreements because those are where the gap lives.
"""
import csv, json, os, random
random.seed(42)
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(REPO, "data", "05_1000videos_ad_systemA_systemB.csv")
MASTER = os.path.join(REPO, "data", "master_transcripts.jsonl")
OUTDIR = os.path.join(REPO, "data", "annotation")
os.makedirs(OUTDIR, exist_ok=True)
N_TARGET = 200

# transcripts by id
tx = {}
for l in open(MASTER, encoding="utf-8"):
    try:
        d = json.loads(l); tx[d["id"]] = d.get("transcript", "")
    except Exception:
        pass

rows = list(csv.DictReader(open(SRC, encoding="utf-8")))
for r in rows:
    r["_disagree"] = (r.get("A_B_agreement", "") != "agree")
    r["_ads"] = (str(r.get("has_player_ads", "")).strip() in ("1", "YES", "yes", "True"))
    r["_stratum"] = ("disagree" if r["_disagree"] else "agree") + "|" + ("ads" if r["_ads"] else "noad")

# 4 mutually-exclusive strata (A=B agreement x ad ground-truth).
# Oversample the disagreement cells (the crux) but keep all 4 represented, and
# record per-stratum sampling so population weights w_h = N_h / n_h are available.
TARGET_N = {"disagree|ads": 70, "disagree|noad": 50, "agree|ads": 50, "agree|noad": 30}
from collections import defaultdict
bystr = defaultdict(list)
for r in rows:
    bystr[r["_stratum"]].append(r)
pop_N = {s: len(v) for s, v in bystr.items()}
pick = []
samp_n = {}
for s, want in TARGET_N.items():
    pool = bystr[s][:]; random.shuffle(pool)
    take = pool[:min(want, len(pool))]
    samp_n[s] = len(take)
    pick += take
weights = {s: round(pop_N[s] / samp_n[s], 3) for s in TARGET_N}
random.shuffle(pick)

# strata documentation
with open(os.path.join(OUTDIR, "annotation_strata.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["stratum", "population_N(of 1000)", "sample_n", "weight_w=N/n"])
    for s in TARGET_N:
        w.writerow([s, pop_N[s], samp_n[s], weights[s]])
    w.writerow(["TOTAL", sum(pop_N.values()), sum(samp_n.values()), ""])

def excerpt(t, n=1500):
    t = " ".join((t or "").split())
    return t[:n]

sample_cols = ["row", "video_id", "youtube_url", "title", "transcript_excerpt",
               "a1_policy_verdict", "a1_folk_verdict", "a2_policy_verdict", "a2_folk_verdict", "notes"]
with open(os.path.join(OUTDIR, "annotation_sample.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh); w.writerow(sample_cols)
    for i, r in enumerate(pick, 1):
        w.writerow([i, r["video_id"], r.get("youtube_url", ""), r.get("title", ""),
                    excerpt(tx.get(r["video_id"], "")), "", "", "", "", ""])

key_cols = ["row", "video_id", "systemA_verdict", "systemB_verdict", "has_player_ads",
            "A_B_agreement", "stratum", "weight"]
with open(os.path.join(OUTDIR, "annotation_key.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh); w.writerow(key_cols)
    for i, r in enumerate(pick, 1):
        w.writerow([i, r["video_id"], r.get("systemA_verdict", ""), r.get("systemB_verdict", ""),
                    "YES" if r["_ads"] else "", r.get("A_B_agreement", ""),
                    r["_stratum"], weights[r["_stratum"]]])

guide = """ANNOTATION GUIDE  -  YouTube self-censorship project, human validation
=====================================================================
You are one of TWO independent annotators. Do NOT discuss videos with the other
annotator until both of you have finished. Fill ONLY your own columns
(annotator 1 -> a1_*, annotator 2 -> a2_*). Leave the machine columns alone
(there are none in your file - that is intentional).

For each row, watch/skim the video via the URL (the transcript_excerpt is a memory
aid, not the whole video) and give TWO verdicts:

1) POLICY verdict (a_policy_verdict):
   Under YouTube's ACTUAL written Advertiser-Friendly Content Guidelines, how
   would THIS video most likely be rated for ads?
      monetise   = fully ad-eligible (green)
      limited    = limited/some ads (yellow) - borderline advertiser-friendliness
      demonetise = not ad-eligible (red) - clearly violates a guideline
   Judge the WRITTEN POLICY as it actually is, not what you fear YouTube does.

2) FOLK verdict (a_folk_verdict):
   How would a typical CREATOR, acting on community lore / fear of the algorithm,
   EXPECT this video to be treated? Same three labels. This captures belief,
   which is often stricter than policy.

Use the same three labels for both. If genuinely unsure, pick the closest and add
a short note in 'notes'. Aim for consistency, not speed.

After both annotators finish, run score_annotation.py to get:
 * Cohen's kappa between the two annotators (policy and folk separately);
 * QUESTION A - do humans also see a policy-vs-folk gap? Reported both on the
   sample AND re-weighted to the full 1000-video population (this sample
   deliberately OVER-samples A!=B disagreements, so the raw sample gap is not the
   population gap - weights w = N_stratum / n_stratum correct for that);
 * QUESTION B - which system is closer to humans? human-policy vs System A,
   human-folk vs System B, and the cross-comparisons, with agreement + kappa;
 * stratified results by the 4 sampling strata;
 * an error table of the biggest human-vs-machine disagreements.

SAMPLING NOTE (for the write-up): the 200 videos are drawn from 4 mutually
exclusive strata = (A=B agreement) x (ad ground-truth). They do not overlap, so
the unique sample size is exactly 200. Per-stratum population sizes, sample sizes
and weights are in annotation_strata.csv. The disagreement-enriched design is for
measurement power on the crux; population-level estimates must use the weights.
"""
open(os.path.join(OUTDIR, "ANNOTATION_GUIDE.txt"), "w", encoding="utf-8").write(guide)
print(f"UNIQUE sample videos: {len(pick)} (strata are mutually exclusive -> no double counting)")
print("per-stratum (population_N | sample_n | weight):")
for s in TARGET_N:
    print(f"   {s:16} {pop_N[s]:4} | {samp_n[s]:3} | w={weights[s]}")
print(f"  overlap (disagree AND ads) is its own stratum 'disagree|ads' = {samp_n['disagree|ads']} videos")
print("wrote annotation_sample.csv, annotation_key.csv, annotation_strata.csv, ANNOTATION_GUIDE.txt ->", OUTDIR)
