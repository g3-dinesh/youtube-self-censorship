import argparse
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from policy_rag import DEFAULT_HOST, DEFAULT_INDEX, DEFAULT_META, load_index
import monetisation_judge as mj
from poc_judge import build_extra, SYSTEM as SYSTEM_A, SCHEMA as SCHEMA_A

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUT = os.path.join(HERE, "..", "data", "perception_reports")

FOLK_RULES_FALLBACK = """COMMON CREATOR FOLK-THEORIES about YouTube demonetisation
(platform lore widely repeated by creators; these are BELIEFS, not official policy):
1. Any swearing (especially f-words) in the FIRST 30 SECONDS instantly demonetises
   the whole video; swearing later is safer.
2. Saying "suicide", "kill", "death", "die", or "rape" out loud triggers a bot flag,
   which is why creators say "unalive", "sewer slide", "grape".
3. Mentioning "covid", "coronavirus", "pandemic", or "vaccine" gets limited ads.
4. Guns, shootings, war, or graphic violence = automatic yellow dollar.
5. Sexual topics, nudity, or LGBTQ+ sexual content = limited or no ads.
6. Discussing tragedies/mass-casualty news in the first minute = demonetised.
7. Heavy profanity throughout = limited ads even if not in the first 30s.
8. Controversial politics, hate speech quotes, or slurs (even when criticising them)
   = demonetised.
9. Drugs, alcohol, gambling references = limited ads.
10. Using algospeak/euphemisms or bleeping words is EVIDENCE the creator expected a
    problem, so lore says the underlying topic is risky."""

FOLK_RULES_JSON = os.path.join(HERE, "..", "data", "folk_corpus", "folk_rules.json")


def load_folk_rules(path=FOLK_RULES_JSON):
    if not os.path.exists(path):
        return FOLK_RULES_FALLBACK
    try:
        d = json.load(open(path, encoding="utf-8"))
        rules = d.get("rules", [])
        if not rules:
            return FOLK_RULES_FALLBACK
    except Exception:
        return FOLK_RULES_FALLBACK
    lines = [
        "CREATOR FOLK-THEORIES about YouTube demonetisation, DISTILLED FROM "
        f"{d.get('n_snippets', '?')} real creator statements scraped from Reddit "
        "(r/PartneredYoutube, r/youtube, r/NewTubers and other creator "
        "subreddits), ranked by how often creators mention them. These are "
        "BELIEFS creators hold, NOT official policy:"]
    for i, r in enumerate(rules, 1):
        line = f"{i}. [{r.get('topic','')}] {r.get('rule','')}"
        if r.get("example"):
            line += f'  Creators say e.g.: "{r["example"][:160]}"'
        lines.append(line)
    return "\n".join(lines)


FOLK_RULES = load_folk_rules()

SYSTEM_B = ("You are simulating how a typical YouTube CREATOR believes the "
            "demonetisation system works, based on widely-shared platform lore and "
            "folk theories, NOT official policy. Apply the listed folk-rules "
            "literally and superstitiously, the way an anxious creator would when "
            "self-censoring before upload. Judge whether a creator would EXPECT "
            "this video to be monetised, limited, or demonetised. Answer with a "
            "single JSON object only.")

SCHEMA_B = """Respond with ONLY this JSON object:
{
  "verdict": "monetise" | "limited" | "demonetise",
  "triggered_folk_rules": [<rule numbers that a creator would think apply>],
  "first_30s_risk": "low" | "medium" | "high",
  "reasoning": "<2-4 sentences in the voice of creator lore>",
  "confidence": "low" | "medium" | "high"
}"""


def first_seconds_text(rec, frac=0.12, cap=1200):
    t = " ".join((rec.get("transcript") or "").split())
    return t[:min(cap, int(len(t) * frac) + 400)]


def judge_official(rec, vid, vectors, records, args):
    hits = mj.retrieve_for_transcript(rec, vectors, records, args.host,
                                      args.embed_model, k=args.k)
    extra, flags = build_extra(rec)
    prompt = mj.build_prompt(rec, hits, extra=extra + "\n\n" + SCHEMA_A)
    raw = mj.call_chat(args.host, args.model, prompt, args.timeout,
                       args.num_ctx, system=SYSTEM_A)
    return mj.parse_verdict(raw), flags


def judge_folk(rec, args):
    head = first_seconds_text(rec)
    body = " ".join((rec.get("transcript") or "").split())
    prompt = "\n".join([
        FOLK_RULES,
        "\n--- VIDEO ---",
        "TITLE: " + (rec.get("title", "") or ""),
        "FIRST ~30 SECONDS OF TRANSCRIPT (folk-rule 1/6 focus):",
        head or "(none)",
        "\nREST OF TRANSCRIPT (truncated):",
        body[:6000] or "(none)",
        "\n" + SCHEMA_B,
    ])
    raw = mj.call_chat(args.host, args.model, prompt, args.timeout,
                       args.num_ctx, system=SYSTEM_B)
    return mj.parse_verdict(raw)


def main():
    ap = argparse.ArgumentParser(
        description="Phase 2: Policy vs Perception. For each video runs TWO Ollama "
                    "judges in parallel -- System A grounded in the OFFICIAL "
                    "advertiser-friendly policy (RAG), System B simulating CREATOR "
                    "FOLK-THEORIES (algospeak lore, 'swearing in first 30s', "
                    "'covid triggers a ban'). Records both verdicts plus the "
                    "creator ground-truth label so you can quantify where real "
                    "policy and platform lore diverge. Laptop Ollama, resumable.")
    ap.add_argument("--video-id")
    ap.add_argument("--from-csv", help="csv with a video_id column")
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
        ids = [(r.get("video_id") or "").strip()
               for r in csv.DictReader(open(args.from_csv, encoding="utf-8-sig"))]
        ids = [v for v in ids if v and v in dataset_idx]
    else:
        sys.exit("need --video-id or --from-csv")
    if args.limit:
        ids = ids[:args.limit]

    os.makedirs(args.out_dir, exist_ok=True)
    if args.resume:
        done = {os.path.splitext(f)[0] for f in os.listdir(args.out_dir)
                if f.endswith(".json") and f != "summary.csv"}
        ids = [v for v in ids if v not in done]

    print(f"A(official) vs B(folk) on {len(ids)} video(s), {args.model} @ "
          f"{args.host}\n")
    rows = []
    n_ab_agree = n_diverge = 0
    for i, vid in enumerate(ids, 1):
        if vid not in dataset_idx:
            continue
        rec = json.load(open(dataset_idx[vid], encoding="utf-8"))
        rec.setdefault("video_id", vid)
        lab = labels.get(vid, {})
        true_label = (lab.get("label", "") or "").strip()
        expected = mj.LABEL_TO_VERDICT.get(true_label.lower(), "")
        try:
            pa, flags = judge_official(rec, vid, vectors, records, args)
            pb = judge_folk(rec, args)
        except Exception as e:
            print(f"[{i}/{len(ids)}] {vid} ERROR: {str(e)[:100]}")
            continue
        va = pa["verdict"] if pa else "PARSE_FAIL"
        vb = pb["verdict"] if pb else "PARSE_FAIL"
        report = {
            "video_id": vid, "title": rec.get("title", ""),
            "creator": lab.get("creator", "") or rec.get("slug", ""),
            "true_label": true_label, "signals": flags,
            "official_A": pa, "folk_B": pb,
        }
        with open(os.path.join(args.out_dir, vid + ".json"), "w",
                  encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=2)
        ab = (va == vb)
        if pa and pb:
            n_ab_agree += int(ab)
            n_diverge += int(not ab)
        rows.append({
            "video_id": vid, "creator": report["creator"],
            "true_label": true_label, "expected_verdict": expected,
            "official_A": va, "folk_B": vb, "A_vs_B_agree": int(ab),
            "A_matches_truth": int(va == expected) if expected else "",
            "B_matches_truth": int(vb == expected) if expected else "",
            "folk_stricter": int(mj_sev(vb) > mj_sev(va)),
            "algospeak_hits": flags.get("algospeak_hits", 0),
            "creator_selfreport": flags.get("creator_selfreport", 0),
        })
        print(f"[{i}/{len(ids)}] {vid:14} A={va:11} B={vb:11} "
              f"{'DIVERGE' if not ab else 'agree'}"
              + (f"  truth={expected}" if expected else ""))

    if rows:
        summ = os.path.join(args.out_dir, "summary.csv")
        with open(summ, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        stricter = sum(r["folk_stricter"] for r in rows)
        print(f"\n{len(rows)} judged | A==B: {n_ab_agree} | diverge: {n_diverge}")
        print(f"folk (B) stricter than policy (A): {stricter}/{len(rows)}  "
              "[the over-perception / self-censorship pressure]")
        ev = [r for r in rows if r["A_matches_truth"] != ""]
        if ev:
            am = sum(r["A_matches_truth"] for r in ev)
            bm = sum(r["B_matches_truth"] for r in ev)
            print(f"vs {len(ev)} labelled: A matches truth {am}, "
                  f"B matches truth {bm}")
        print(f"-> {summ}")


def mj_sev(v):
    return {"monetise": 0, "limited": 1, "demonetise": 2}.get(v, 0)


if __name__ == "__main__":
    main()
