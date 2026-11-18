import argparse
import csv
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from policy_rag import DEFAULT_HOST, DEFAULT_INDEX, DEFAULT_META, load_index
import monetisation_judge as mj
from poc_find_demonetisation import (DEMON_TERMS, CREATOR_STRONG, find_snippets,
                                     scan_comments)
from poc_self_censorship import scan as scan_censorship, STOPWORDS

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUT = os.path.join(HERE, "..", "data", "poc_judge_reports")

SYSTEM = ("You are a careful YouTube monetisation policy reviewer for a research "
          "study. You receive RETRIEVED official advertiser-friendly policy "
          "sections and MULTIPLE SIGNALS from one video: its title/description, "
          "transcript evidence, top viewer comments, whether the creator or "
          "commenters SELF-REPORT a monetisation problem, and any self-censorship "
          "(word-swapping / algospeak) detected in the transcript. Judge ONLY "
          "whether the content SHOULD be monetised under the published policy. You "
          "are NOT predicting YouTube's opaque decision. Treat self-report and "
          "self-censorship as weak corroborating signals, never as proof. Ground "
          "every claim in the supplied evidence, cite the policy category, and say "
          "which signal drove the call. Answer with a single JSON object only.")

SCHEMA = """Respond with ONLY this JSON object:
{
  "verdict": "monetise" | "limited" | "demonetise",
  "risk": "low" | "medium" | "high",
  "primary_signal": "transcript" | "comments" | "self_report" | "self_censorship" | "none",
  "policy_areas": [
    {"category":"<retrieved category>","evidence":"<what triggers it>",
     "policy":"<what the policy says>","assessment":"<call + why>"}
  ],
  "self_report_note": "<what the creator/comments claim about monetisation, or none>",
  "self_censorship_note": "<word-swaps the creator used to stay ad-safe, or none>",
  "overall_reasoning": "<2-5 sentences tying signals to policy>",
  "confidence": "low" | "medium" | "high"
}
If nothing is triggered, return empty policy_areas and verdict "monetise"."""


def top_comments_block(rec, n=8):
    comments = rec.get("comments") or []
    demon = []
    other = []
    for c in comments:
        text = re.sub(r"\s+", " ", (c.get("text") or "")).strip()
        if not text:
            continue
        low = text.lower()
        likes = c.get("like_count") or 0
        if any(t in low for t in DEMON_TERMS):
            demon.append((likes, text))
        else:
            other.append((likes, text))
    demon.sort(reverse=True)
    other.sort(reverse=True)
    picked = demon[:n] + other[:max(0, n - len(demon))]
    lines = []
    for likes, text in picked[:n]:
        lines.append(f"- ({likes} likes) {text[:220]}")
    return "\n".join(lines)


def build_extra(rec):
    transcript = rec.get("transcript") or ""
    desc = rec.get("description") or ""
    title = rec.get("title") or ""

    t_hits = find_snippets(title + ". " + transcript, CREATOR_STRONG)
    d_hits = find_snippets(desc, DEMON_TERMS)
    n_viewer, n_creator, top_comment, top_by_creator = scan_comments(rec)
    algo, meta, masks = scan_censorship(transcript)
    algo_kept = {k: v for k, v in algo.items() if k not in STOPWORDS}

    parts = []
    parts.append("\n--- TOP VIEWER COMMENTS (data, may be noisy) ---")
    cb = top_comments_block(rec)
    parts.append(cb if cb else "(no comments collected)")

    sr = []
    if t_hits:
        sr.append(f"creator says in transcript: \"{t_hits[0][1][:200]}\"")
    if d_hits:
        sr.append(f"creator says in description: \"{d_hits[0][1][:200]}\"")
    if n_creator:
        sr.append(f"creator's own comment mentions it "
                  f"({n_creator} comment(s)): \"{top_comment[:200]}\"")
    elif n_viewer and top_comment:
        sr.append(f"{n_viewer} viewer comment(s) mention monetisation, e.g. "
                  f"\"{top_comment[:200]}\"")
    parts.append("\n--- SELF-REPORT SIGNAL ---")
    parts.append("\n".join(sr) if sr else "none detected")

    parts.append("\n--- SELF-CENSORSHIP SIGNAL (transcript word-swaps) ---")
    if algo_kept or sum(meta.values()) or masks:
        bits = []
        if algo_kept:
            bits.append("algospeak: " + ", ".join(
                f"{k} x{v}" for k, v in sorted(algo_kept.items())))
        if meta:
            bits.append("meta-phrases: " + ", ".join(sorted(meta)))
        if masks:
            bits.append(f"masked spellings: {masks}")
        parts.append("; ".join(bits))
    else:
        parts.append("none detected")

    flags = {
        "creator_selfreport": 1 if (t_hits or d_hits or n_creator) else 0,
        "viewer_selfreport": int(n_viewer),
        "algospeak_hits": int(sum(algo_kept.values())),
        "meta_phrase_hits": int(sum(meta.values())),
        "masked_words": int(masks),
    }
    return "\n".join(parts), flags


def judge_one(rec, vid, vectors, records, labels, args):
    hits = mj.retrieve_for_transcript(rec, vectors, records, args.host,
                                      args.embed_model, k=args.k)
    extra, flags = build_extra(rec)
    prompt = mj.build_prompt(rec, hits, extra=extra + "\n\n" + SCHEMA)
    raw = mj.call_chat(args.host, args.model, prompt, args.timeout,
                       args.num_ctx, system=SYSTEM)
    parsed = mj.parse_verdict(raw)
    lab = labels.get(vid or "", {})
    true_label = (lab.get("label", "") or "").strip()
    expected = mj.LABEL_TO_VERDICT.get(true_label.lower(), "")
    report = {
        "video_id": vid or "",
        "title": rec.get("title", ""),
        "creator": lab.get("creator", "") or rec.get("slug", ""),
        "true_label": true_label,
        "signals": flags,
        "retrieved_policies": [
            {"category": h["record"]["category"], "score": round(h["score"], 3)}
            for h in hits],
        "verdict": parsed,
        "raw": None if parsed else raw[:500],
    }
    if parsed and expected:
        report["agree"] = (parsed["verdict"] == expected)
    return report, parsed, flags, true_label, expected


def main():
    ap = argparse.ArgumentParser(
        description="Proof-of-concept multi-signal monetisation judge. Fuses "
                    "transcript + top comments + creator/viewer self-report + "
                    "self-censorship (algospeak) with RAG policy retrieval and an "
                    "open-source Ollama model (default qwen3:8b on the laptop, "
                    "localhost). One video (--video-id) or a whole self-report set "
                    "(--from-csv). Resumable.")
    ap.add_argument("--video-id", help="id in data/dataset/<slug>/")
    ap.add_argument("--from-csv",
                    help="csv with a video_id column (e.g. the self-report set) "
                         "to judge in batch")
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
    ap.add_argument("--out-dir", default=DEFAULT_OUT)
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()

    if not (os.path.exists(args.index) and os.path.exists(args.meta)):
        sys.exit("no policy index; run 'policy_rag.py build' first")
    vectors, records, _ = load_index(args.index, args.meta)
    dataset_idx = mj.build_dataset_index()
    labels = mj.load_labels(args.labels)

    if args.video_id:
        ids = [args.video_id]
    elif args.from_csv:
        ids = []
        for r in csv.DictReader(open(args.from_csv, encoding="utf-8-sig")):
            v = (r.get("video_id") or "").strip()
            if v and v in dataset_idx:
                ids.append(v)
    else:
        sys.exit("need --video-id or --from-csv")
    if args.limit:
        ids = ids[:args.limit]

    os.makedirs(args.out_dir, exist_ok=True)
    if args.resume:
        done = {os.path.splitext(f)[0] for f in os.listdir(args.out_dir)
                if f.endswith(".json") and f != "summary.csv"}
        ids = [v for v in ids if v not in done]

    single = bool(args.video_id) and not args.from_csv
    print(f"judging {len(ids)} video(s) on {args.model} @ {args.host}\n")
    rows = []
    for i, vid in enumerate(ids, 1):
        if vid not in dataset_idx:
            print(f"[{i}/{len(ids)}] {vid} NOT in dataset, skip")
            continue
        rec = json.load(open(dataset_idx[vid], encoding="utf-8"))
        rec.setdefault("video_id", vid)
        try:
            report, parsed, flags, true_label, expected = judge_one(
                rec, vid, vectors, records, labels, args)
        except Exception as e:
            print(f"[{i}/{len(ids)}] {vid} ERROR: {str(e)[:100]}")
            continue
        with open(os.path.join(args.out_dir, vid + ".json"), "w",
                  encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=2)
        v = parsed["verdict"].upper() if parsed else "PARSE_FAIL"
        rows.append({
            "video_id": vid, "creator": report["creator"],
            "true_label": true_label,
            "verdict": parsed["verdict"] if parsed else "PARSE_FAIL",
            "primary_signal": parsed.get("primary_signal", "") if parsed else "",
            "agree": report.get("agree", ""),
            "creator_selfreport": flags["creator_selfreport"],
            "viewer_selfreport": flags["viewer_selfreport"],
            "algospeak_hits": flags["algospeak_hits"],
        })
        sig = (f"sr={flags['creator_selfreport']} vr={flags['viewer_selfreport']} "
               f"algo={flags['algospeak_hits']}")
        print(f"[{i}/{len(ids)}] {vid:14} -> {v:11} [{sig}]"
              + (f" true={true_label}" if true_label else ""))
        if single and parsed:
            print("\n" + "=" * 70)
            print("primary signal:", parsed.get("primary_signal", "?"))
            print("self-report:", parsed.get("self_report_note", ""))
            print("self-censorship:", parsed.get("self_censorship_note", ""))
            print("reasoning:", parsed.get("overall_reasoning", ""))
            for pa in parsed.get("policy_areas", []):
                print(f"  - {pa.get('category','?')}: {pa.get('assessment','')}")

    if rows:
        summ = os.path.join(args.out_dir, "summary.csv")
        with open(summ, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        dem = sum(1 for r in rows if r["verdict"] == "demonetise")
        lim = sum(1 for r in rows if r["verdict"] == "limited")
        mon = sum(1 for r in rows if r["verdict"] == "monetise")
        print(f"\n{len(rows)} judged: demonetise={dem} limited={lim} monetise={mon}")
        print(f"-> {summ}")


if __name__ == "__main__":
    main()
