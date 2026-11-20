"""#1 aggregation — summarise the qwen3 advice-rule classification (out1.jsonl)
into the Folk-Theory-Alignment table used in Results_Exp1_AdviceFraming.txt.

Input : data/out1.jsonl  (one object per advice video, from exp1_advice_rules.py)
Output: prints the folk/policy/platform breakdown + Folk-Theory Alignment.
"""
import json, os, collections
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INP = os.path.join(REPO, "data", "out1.jsonl")


def main():
    rows = [json.loads(l) for l in open(INP, encoding="utf-8") if l.strip()]
    F = sum(r["folk"] for r in rows); P = sum(r["policy"] for r in rows)
    PL = sum(r["platform"] for r in rows); O = sum(r["other"] for r in rows)
    tot = F + P + PL + O
    print(f"advice videos           : {len(rows)}")
    print(f"total rules extracted   : {tot}")
    print(f"  folk      {F:4}  ({100*F/tot:.1f}%)")
    print(f"  policy    {P:4}  ({100*P/tot:.1f}%)")
    print(f"  platform  {PL:4}  ({100*PL/tot:.1f}%)")
    print(f"  other     {O:4}  ({100*O/tot:.1f}%)")
    fp = F + P
    print(f"FOLK-THEORY ALIGNMENT folk/(folk+policy) = {100*F/fp:.1f}%" if fp else "n/a")
    fd = sum(1 for r in rows if r["folk"] > r["policy"])
    pd = sum(1 for r in rows if r["policy"] > r["folk"])
    print(f"folk-dominant videos {fd}/{len(rows)} ; policy-dominant {pd}/{len(rows)}")
    w = collections.Counter()
    for r in rows:
        for rl in r.get("rules", []):
            if rl.get("trigger_word"):
                w[rl["trigger_word"].lower()[:24]] += 1
    print("top cited triggers:", w.most_common(8))


if __name__ == "__main__":
    main()
