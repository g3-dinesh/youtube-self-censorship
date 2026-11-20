"""#2 (supervisor) — score human annotations: measurement validity for the A-vs-B gap.

Separates the supervisor's two questions:
  QUESTION A  Do HUMANS also see a large policy-vs-folk gap? (validity of the gap)
              -> reported UNWEIGHTED (on the sample) AND WEIGHTED to the 1000-video
                 population (inverse-probability weights w=N_h/n_h), because the
                 sample deliberately over-samples A!=B disagreements.
  QUESTION B  WHICH SYSTEM is closer to human judgement? (validity of A and B as
              instruments) -> human-policy vs System A, human-folk vs System B,
              and cross (human-policy vs B, human-folk vs A), with agreement+kappa.

Also: inter-annotator Cohen kappa; results STRATIFIED by the 4 strata; and an
error table. Run after BOTH annotators fill a1_*/a2_*.

Run: python score_annotation.py   (needs sklearn)
"""
import csv, os, collections
from sklearn.metrics import cohen_kappa_score
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
D = os.path.join(REPO, "data", "annotation")
LAB = {"monetise": 0, "limited": 1, "demonetise": 2}


def norm(v):
    v = (v or "").strip().lower()
    return v if v in LAB else ""


def demon_rate(vals, weights=None):
    """% demonetise; optionally weighted."""
    if weights is None:
        return 100 * sum(1 for v in vals if v == "demonetise") / len(vals) if vals else float("nan")
    num = sum(w for v, w in zip(vals, weights) if v == "demonetise")
    den = sum(weights)
    return 100 * num / den if den else float("nan")


def main():
    samp = {r["row"]: r for r in csv.DictReader(open(os.path.join(D, "annotation_sample.csv"), encoding="utf-8"))}
    key = {r["row"]: r for r in csv.DictReader(open(os.path.join(D, "annotation_key.csv"), encoding="utf-8"))}
    rows = [rw for rw in samp if norm(samp[rw]["a1_policy_verdict"]) and norm(samp[rw]["a2_policy_verdict"])]
    out = []
    def P(s): out.append(s); print(s)
    if not rows:
        print("No completed annotations yet. Both annotators must fill a1_* and a2_* first.")
        print("(Strata/weights are already in annotation_key.csv and annotation_strata.csv.)")
        return

    # ---- inter-annotator agreement ----
    a1p = [LAB[norm(samp[r]["a1_policy_verdict"])] for r in rows]
    a2p = [LAB[norm(samp[r]["a2_policy_verdict"])] for r in rows]
    folk_rows = [r for r in rows if norm(samp[r]["a1_folk_verdict"]) and norm(samp[r]["a2_folk_verdict"])]
    P("=" * 64)
    P(f"HUMAN VALIDATION   (n={len(rows)} doubly-annotated; folk n={len(folk_rows)})")
    P("=" * 64)
    P(f"Inter-annotator Cohen kappa  POLICY : {cohen_kappa_score(a1p, a2p):.3f}")
    if folk_rows:
        P(f"Inter-annotator Cohen kappa  FOLK   : "
          f"{cohen_kappa_score([LAB[norm(samp[r]['a1_folk_verdict'])] for r in folk_rows], [LAB[norm(samp[r]['a2_folk_verdict'])] for r in folk_rows]):.3f}")
    P("  (kappa >=0.6 substantial, >=0.4 moderate; <0.4 => refine protocol/definitions)")

    # human majority (tie -> annotator 1; flag count)
    ties = 0
    def majority(r, pref):
        v1 = norm(samp[r][f"a1_{pref}"]); v2 = norm(samp[r][f"a2_{pref}"])
        if v1 == v2: return v1
        return v1
    hum_pol = {r: majority(r, "policy_verdict") for r in rows}
    hum_folk = {r: majority(r, "folk_verdict") for r in rows}
    W = {r: float(key[r]["weight"]) for r in rows}

    # ---- QUESTION A: human gap, unweighted + weighted ----
    P("")
    P("-- QUESTION A: do humans see a policy-vs-folk gap? --")
    hp_u = demon_rate([hum_pol[r] for r in rows if hum_pol[r]])
    hf_u = demon_rate([hum_folk[r] for r in rows if hum_folk[r]])
    P(f"  UNWEIGHTED (sample): policy-demon {hp_u:.0f}%  folk-demon {hf_u:.0f}%  gap {hf_u-hp_u:+.0f}pp")
    pr = [(hum_pol[r], W[r]) for r in rows if hum_pol[r]]
    fr = [(hum_folk[r], W[r]) for r in rows if hum_folk[r]]
    hp_w = demon_rate([v for v, _ in pr], [w for _, w in pr])
    hf_w = demon_rate([v for v, _ in fr], [w for _, w in fr])
    P(f"  WEIGHTED to 1000-pop: policy-demon {hp_w:.0f}%  folk-demon {hf_w:.0f}%  gap {hf_w-hp_w:+.0f}pp")
    P(f"  (machine on same metric: System A ~19%, System B ~76%)")

    # ---- QUESTION B: which system is closer to humans? ----
    P("")
    P("-- QUESTION B: which system matches human judgement? --")
    A = {r: norm(key[r]["systemA_verdict"]) for r in rows}
    B = {r: norm(key[r]["systemB_verdict"]) for r in rows}
    def cmp(h, m):
        pr = [(h[r], m[r]) for r in rows if h[r] and m[r]]
        acc = sum(1 for a, b in pr if a == b) / len(pr)
        ka = cohen_kappa_score([LAB[a] for a, _ in pr], [LAB[b] for _, b in pr])
        return acc, ka, len(pr)
    for name, h, m in [("human-POLICY vs System A", hum_pol, A),
                       ("human-POLICY vs System B", hum_pol, B),
                       ("human-FOLK   vs System A", hum_folk, A),
                       ("human-FOLK   vs System B", hum_folk, B)]:
        acc, ka, n = cmp(h, m)
        P(f"  {name}: agree {100*acc:3.0f}%  kappa {ka:+.3f}  (n={n})")
    P("  Strong validation = human-POLICY closest to A AND human-FOLK closest to B.")

    # ---- stratified Question A ----
    P("")
    P("-- STRATIFIED (human policy-demon vs folk-demon by stratum) --")
    strata = collections.defaultdict(list)
    for r in rows:
        strata[key[r]["stratum"]].append(r)
    for s, rs in sorted(strata.items()):
        hp = demon_rate([hum_pol[r] for r in rs if hum_pol[r]])
        hf = demon_rate([hum_folk[r] for r in rs if hum_folk[r]])
        P(f"  {s:16} n={len(rs):3}  policy {hp:3.0f}%  folk {hf:3.0f}%  gap {hf-hp:+.0f}pp")

    # ---- error table ----
    P("")
    P("Largest human-POLICY vs System A disagreements:")
    for r in [r for r in rows if hum_pol[r] and A[r] and hum_pol[r] != A[r]][:12]:
        P(f"  row {r}: human={hum_pol[r]:10} A={A[r]:10} id={key[r]['video_id']}")

    open(os.path.join(D, "annotation_scored.txt"), "w", encoding="utf-8").write("\n".join(out))
    print("\n-> saved annotation_scored.txt")


if __name__ == "__main__":
    main()
