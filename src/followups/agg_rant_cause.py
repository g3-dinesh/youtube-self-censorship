"""#2 aggregation — summarise the qwen3 rant cause-attribution (out2.jsonl) into
the policy/folk table used in Results_Exp2_RantCause.txt.

Input : data/out2.jsonl  (one object per rant video, from exp2_rant_cause.py)
Output: prints cause_type distribution + top blamed labels.
"""
import json, os, collections
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INP = os.path.join(REPO, "data", "out2.jsonl")


def main():
    rows = [json.loads(l) for l in open(INP, encoding="utf-8") if l.strip()]
    ct = collections.Counter(r["cause_type"] for r in rows)
    cl = collections.Counter(r["cause_label"] for r in rows)
    tot = sum(ct.values())
    print(f"rant videos : {len(rows)}")
    for k in ["policy", "folk", "other", "none_stated"]:
        if ct.get(k):
            print(f"  {k:12} {ct[k]:3}  ({100*ct[k]/tot:.0f}%)")
    print("top blamed labels:", cl.most_common(10))


if __name__ == "__main__":
    main()
