"""STAGE 3 - System A judge: OFFICIAL POLICY.

Judges whether a video SHOULD be monetised under YouTube's *written*
advertiser-friendly guidelines. It retrieves the policy sections the transcript
actually touches (RAG over data/policy_corpus) and asks an Ollama model
(qwen3:8b on the GPU server) for a grounded monetise / limited / demonetise
verdict with a cited policy category.

This is the "ground truth of the rules" half of the A-vs-B comparison. System B
(07) judges the same videos by creator *folk belief*; the gap between them is the
thesis.

Requires: the Ollama server reachable at --host (default http://localhost:11434),
and the policy index in data/policy_corpus/ (bundled).

Input
  --video-id ONE id present in data/dataset/, OR --from-csv a CSV with a
  video_id column (e.g. data/ground_truth_labels.csv)

Output
  outputs/system_a_verdicts.csv   video_id, creator, true_label, verdict,
                                  risk, confidence
  per-video JSON in outputs/system_a_reports/

Example
  python src/06_system_a_judge.py --from-csv data/ground_truth_labels.csv --limit 10
  python src/06_system_a_judge.py --video-id <id> --host http://192.168.144.226:11434
"""
import argparse, csv, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from policy_rag import DEFAULT_HOST, DEFAULT_INDEX, DEFAULT_META, load_index
import monetisation_judge as mj
from poc_perception_judge import judge_official

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "outputs", "system_a_reports")


def main():
    ap = argparse.ArgumentParser(description="System A - official-policy judge.")
    ap.add_argument("--video-id")
    ap.add_argument("--from-csv", help="CSV with a video_id column")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--index", default=DEFAULT_INDEX)
    ap.add_argument("--meta", default=DEFAULT_META)
    ap.add_argument("--labels", default=mj.DEFAULT_LABELS)
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--model", default=mj.DEFAULT_CHAT_MODEL)
    ap.add_argument("--embed-model", default=mj.DEFAULT_EMBED_MODEL)
    ap.add_argument("-k", type=int, default=5)
    ap.add_argument("--num-ctx", type=int, default=8192)
    ap.add_argument("--timeout", type=float, default=300.0)
    args = ap.parse_args()

    if not (os.path.exists(args.index) and os.path.exists(args.meta)):
        sys.exit("policy index missing in data/policy_corpus/")
    vectors, records, _ = load_index(args.index, args.meta)
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
    print(f"System A (official policy) on {len(ids)} video(s), {args.model} @ {args.host}\n")
    rows = []
    for i, vid in enumerate(ids, 1):
        if vid not in dataset_idx:
            continue
        rec = json.load(open(dataset_idx[vid], encoding="utf-8")); rec.setdefault("video_id", vid)
        lab = labels.get(vid, {})
        try:
            parsed, flags = judge_official(rec, vid, vectors, records, args)
        except Exception as e:
            print(f"[{i}/{len(ids)}] {vid} ERROR: {str(e)[:90]}"); continue
        verdict = parsed["verdict"] if parsed else "PARSE_FAIL"
        json.dump({"video_id": vid, "verdict": parsed, "signals": flags},
                  open(os.path.join(OUT, vid + ".json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        reasoning = (parsed.get("overall_reasoning", "") if parsed else "") or ""
        cats = "; ".join(p.get("category", "") for p in (parsed.get("policy_areas") or [])) if parsed else ""
        rows.append({"video_id": vid, "creator": lab.get("creator", "") or rec.get("slug", ""),
                     "true_label": (lab.get("label", "") or "").strip(), "verdict": verdict,
                     "risk": parsed.get("risk", "") if parsed else "",
                     "confidence": parsed.get("confidence", "") if parsed else "",
                     "policy_areas": cats, "reasoning": reasoning})
        print(f"[{i}/{len(ids)}] {vid:14} -> A={verdict}  (risk={parsed.get('risk', '') if parsed else ''})")
        if cats:
            print(f"      policy : {cats}")
        if reasoning:
            print(f"      reason : {reasoning[:300]}")

    if rows:
        out_csv = os.path.join(HERE, "..", "outputs", "system_a_verdicts.csv")
        with open(out_csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
        print(f"\n-> {out_csv}")


if __name__ == "__main__":
    main()
