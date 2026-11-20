"""#1b aggregation — creator-level Talk-vs-Walk pairing.

Pairs each matched creator's TALK (folk-loading from their own demonetisation
video, scored by exp1_advice_rules.py -> out_ctalk.jsonl) with their WALK
(validated strict masking rate, self_censorship_by_creator.csv).
Produces the table in Results_Exp1b_CreatorLevel_TalkVsWalk.txt.

Inputs : data/creator_talk.jsonl, data/out_ctalk.jsonl,
         data/experiments/self_censorship_by_creator.csv
"""
import json, os, csv
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    mask = {}
    with open(os.path.join(REPO, "data", "experiments", "self_censorship_by_creator.csv"), encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            mask[row["creator"]] = float(row["flagged_pct"])
    talk = {json.loads(l)["id"]: json.loads(l)
            for l in open(os.path.join(REPO, "data", "out_ctalk.jsonl"), encoding="utf-8")}
    meta = {}
    for l in open(os.path.join(REPO, "data", "creator_talk.jsonl"), encoding="utf-8"):
        r = json.loads(l); meta[r["id"]] = (r["handle"], r["name"], r["title"])

    print(f"{'creator':18}{'talk_folk%':>11}{'rules f/p/plat':>16}{'walk_mask%':>12}")
    for vid, t in talk.items():
        handle, name, _ = meta.get(vid, (vid, vid, ""))
        f, p, pl = t["folk"], t["policy"], t["platform"]
        folkpct = 100 * f / (f + p) if (f + p) else 0
        mk = mask.get(handle)
        print(f"{name[:18]:18}{folkpct:9.0f}%  {f}/{p}/{pl:<10}"
              f"{(str(mk)+'%') if mk is not None else 'n/a':>12}")


if __name__ == "__main__":
    main()
