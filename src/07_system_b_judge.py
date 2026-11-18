"""STAGE 3 - System B judge: CREATOR FOLK BELIEF.

Judges the same videos the way an anxious YouTube CREATOR believes the system
works - applying widely-shared platform lore ("swearing in the first 30 seconds
demonetises you", "saying 'suicide' triggers a bot") literally and
superstitiously. The folk rules are DISTILLED FROM REAL CREATOR POSTS
(data/folk_corpus/folk_rules.json) rather than invented.

System B is the "what creators fear" half of the comparison. Where B is stricter
than System A (06, the real policy), creators are self-censoring for a rule that
does not exist - the project's core finding.

Note on data source: the folk rules were mined from creator discussion archives
(Reddit is API-blocked, so we use the Arctic Shift archive). Same judge model
(Ollama qwen3:8b) as System A, for a fair comparison.

Input / Output: identical shape to 06, but writes System-B verdicts.
  outputs/system_b_verdicts.csv, outputs/system_b_reports/

Example
  python src/07_system_b_judge.py --from-csv data/ground_truth_labels.csv --limit 10
"""
import argparse, csv, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from policy_rag import DEFAULT_HOST, DEFAULT_INDEX, DEFAULT_META, load_index
import monetisation_judge as mj
from poc_perception_judge import judge_folk, FOLK_RULES

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "outputs", "system_b_reports")


def main():
    ap = argparse.ArgumentParser(description="System B - creator folk-belief judge.")
    ap.add_argument("--video-id")
    ap.add_argument("--from-csv", help="CSV with a video_id column")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--labels", default=mj.DEFAULT_LABELS)
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--model", default=mj.DEFAULT_CHAT_MODEL)
    ap.add_argument("--embed-model", default=mj.DEFAULT_EMBED_MODEL)
    ap.add_argument("-k", type=int, default=5)
    ap.add_argument("--num-ctx", type=int, default=8192)
    ap.add_argument("--timeout", type=float, default=300.0)
    args = ap.parse_args()

    dataset_idx = mj.build_dataset_index()
    labels = mj.load_labels(args.labels)

    if args.video_id:
        ids = [args.video_id]
    elif args.from_csv:
        ids = [(r.get("video_id") or "").strip()
               for r in csv.DictReader(open(args.from_csv, encoding="utf-8-sig"))]
        ids = [v for v in ids if v and v in dataset_idx]
    else:
        sys.exit("need --video-id or --from-csv")
    if args.limit:
        ids = ids[:args.limit]

    os.makedirs(OUT, exist_ok=True)
    print(f"System B (creator folk belief) on {len(ids)} video(s), {args.model} @ {args.host}")
    print(f"folk rules loaded: {FOLK_RULES[:70]}...\n")
    rows = []
    for i, vid in enumerate(ids, 1):
        if vid not in dataset_idx:
            continue
        rec = json.load(open(dataset_idx[vid], encoding="utf-8")); rec.setdefault("video_id", vid)
        lab = labels.get(vid, {})
        try:
            parsed = judge_folk(rec, args)
        except Exception as e:
            print(f"[{i}/{len(ids)}] {vid} ERROR: {str(e)[:90]}"); continue
        verdict = parsed["verdict"] if parsed else "PARSE_FAIL"
        json.dump({"video_id": vid, "verdict": parsed},
                  open(os.path.join(OUT, vid + ".json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        rows.append({"video_id": vid, "creator": lab.get("creator", "") or rec.get("slug", ""),
                     "true_label": (lab.get("label", "") or "").strip(), "verdict": verdict,
                     "first_30s_risk": parsed.get("first_30s_risk", "") if parsed else "",
                     "confidence": parsed.get("confidence", "") if parsed else ""})
        print(f"[{i}/{len(ids)}] {vid:14} -> B={verdict}")

    if rows:
        out_csv = os.path.join(HERE, "..", "outputs", "system_b_verdicts.csv")
        with open(out_csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
        print(f"\n-> {out_csv}")


if __name__ == "__main__":
    main()
