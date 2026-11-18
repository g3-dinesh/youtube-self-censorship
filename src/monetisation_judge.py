import argparse
import glob
import json
import os
import sys
import urllib.request

import numpy as np

from policy_rag import (DEFAULT_HOST, DEFAULT_INDEX, DEFAULT_META,
                        embed_texts, load_index)

HERE = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(HERE, "..", "data", "dataset")
DEFAULT_LABELS = os.path.join(HERE, "..", "data", "ground_truth_labels.csv")
DEFAULT_OUT = os.path.join(HERE, "..", "data", "judge_reports")
DEFAULT_CHAT_MODEL = "qwen3:8b"
DEFAULT_EMBED_MODEL = "nomic-embed-text"

SYSTEM = ("You are a careful YouTube monetisation policy reviewer. You are given "
          "a set of RETRIEVED official policy sections and a video's title, "
          "description, and transcript evidence. Judge ONLY whether the video's "
          "content should be monetised under those published policies. You are "
          "NOT predicting YouTube's actual opaque decision. Ground every claim in "
          "the supplied evidence and cite the policy category. Answer with a "
          "single JSON object and nothing else.")

SCHEMA_HINT = """Respond with ONLY this JSON object:
{
  "verdict": "monetise" | "limited" | "demonetise",
  "risk": "low" | "medium" | "high",
  "policy_areas": [
    {
      "category": "<retrieved policy category>",
      "evidence": "<what in the video triggers it, quoting the transcript>",
      "policy": "<what that policy says>",
      "assessment": "<monetise/limited/demonetise for this area and why>"
    }
  ],
  "overall_reasoning": "<2-5 sentences tying evidence to policy>",
  "confidence": "low" | "medium" | "high"
}
If no policy area is triggered, return an empty policy_areas list and verdict
"monetise"."""


def windows(text, size=900, overlap=150):
    text = " ".join((text or "").split())
    if not text:
        return []
    out = []
    step = max(1, size - overlap)
    for i in range(0, len(text), step):
        piece = text[i:i + size]
        if piece:
            out.append(piece)
        if i + size >= len(text):
            break
    return out


def retrieve_for_transcript(rec, vectors, records, host, embed_model, k=5,
                            n_windows=40):
    title = rec.get("title", "") or ""
    desc = rec.get("description", "") or ""
    transcript = rec.get("transcript", "") or ""
    wins = windows(transcript)[:n_windows]
    probes = [p for p in [title, desc] if p] + wins
    if not probes:
        return []
    pv = embed_texts(host, embed_model, probes)
    sims = vectors @ pv.T
    best_win = sims.argmax(axis=1)
    best_score = sims.max(axis=1)
    order = np.argsort(-best_score)[:k]
    hits = []
    for i in order:
        hits.append({
            "record": records[i],
            "score": float(best_score[i]),
            "evidence": probes[int(best_win[i])],
        })
    return hits


def build_prompt(rec, hits, max_evidence_chars=600, extra=None):
    lines = ["RETRIEVED POLICY SECTIONS (official YouTube guidance):"]
    for h in hits:
        r = h["record"]
        lines.append(f"\n### {r['category']}  (source: {r['source']})")
        lines.append(f"Rule: {r['rule']}")
        if r.get("monetizable"):
            lines.append(f"Can monetise: {r['monetizable']}")
        if r.get("limited"):
            lines.append(f"Limited/age-restricted: {r['limited']}")
        if r.get("no_ads"):
            lines.append(f"No ads: {r['no_ads']}")
        lines.append(f"Most relevant transcript passage: "
                     f"\"{h['evidence'][:max_evidence_chars]}\"")
    lines.append("\n--- VIDEO ---")
    lines.append("TITLE: " + (rec.get("title", "") or ""))
    desc = rec.get("description", "") or ""
    lines.append("DESCRIPTION: " + (desc[:1500] if desc else "(none)"))
    if extra:
        lines.append(extra)
    lines.append("\n" + SCHEMA_HINT)
    return "\n".join(lines)


def call_chat(host, model, prompt, timeout, num_ctx, system=None,
              num_predict=2048):
    url = host.rstrip("/") + "/api/chat"
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system or SYSTEM},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "format": "json",
        "think": False,
        "options": {"temperature": 0, "num_ctx": num_ctx,
                    "num_predict": num_predict},
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        out = json.loads(resp.read().decode("utf-8"))
    return out.get("message", {}).get("content", "")


def _norm_verdict(v):
    v = str(v).strip().lower()
    return {"monetize": "monetise", "demonetize": "demonetise"}.get(v, v)


def parse_verdict(raw):
    try:
        obj = json.loads(raw)
        v = _norm_verdict(obj.get("verdict", ""))
        if v in ("monetise", "limited", "demonetise"):
            obj["verdict"] = v
            return obj
    except Exception:
        pass
    import re
    m = re.search(r'"verdict"\s*:\s*"([^"]+)"', raw or "")
    if m:
        v = _norm_verdict(m.group(1))
        if v in ("monetise", "limited", "demonetise"):
            out = {"verdict": v, "truncated": True, "policy_areas": []}
            rm = re.search(r'"risk"\s*:\s*"([^"]+)"', raw)
            cm = re.search(r'"confidence"\s*:\s*"([^"]+)"', raw)
            om = re.search(r'"overall_reasoning"\s*:\s*"([^"]+)"', raw)
            if rm:
                out["risk"] = rm.group(1)
            if cm:
                out["confidence"] = cm.group(1)
            if om:
                out["overall_reasoning"] = om.group(1)
            return out
    return None


def build_dataset_index():
    idx = {}
    for path in glob.glob(os.path.join(DATASET_DIR, "*", "*.json")):
        vid = os.path.splitext(os.path.basename(path))[0]
        idx[vid] = path
    return idx


def load_labels(path):
    import csv
    rows = {}
    if path and os.path.exists(path):
        for r in csv.DictReader(open(path, encoding="utf-8-sig")):
            vid = (r.get("video_id") or "").strip()
            if vid:
                rows[vid] = r
    return rows


LABEL_TO_VERDICT = {
    "demonetised": "demonetise", "demonetized": "demonetise",
    "monetised": "monetise", "monetized": "monetise",
    "limited_ads": "limited", "limited": "limited",
}


def make_record(args, dataset_idx):
    if args.transcript_file:
        with open(args.transcript_file, encoding="utf-8") as fh:
            return {"title": args.title or "", "description": args.description or "",
                    "transcript": fh.read(), "video_id": args.video_id or ""}, None
    if args.video_id and args.video_id in dataset_idx:
        with open(dataset_idx[args.video_id], encoding="utf-8") as fh:
            rec = json.load(fh)
        rec.setdefault("video_id", args.video_id)
        return rec, args.video_id
    sys.exit("need --transcript-file, or a --video-id present in data/dataset")


def judge_video(rec, vid, vectors, records, labels, args):
    hits = retrieve_for_transcript(rec, vectors, records, args.host,
                                   args.embed_model, k=args.k)
    prompt = build_prompt(rec, hits)
    raw = call_chat(args.host, args.model, prompt, args.timeout, args.num_ctx)
    parsed = parse_verdict(raw)
    lab = labels.get(vid or "", {})
    true_label = (lab.get("label", "") or "").strip()
    expected = LABEL_TO_VERDICT.get(true_label.lower(), "")
    report = {
        "video_id": vid or "",
        "title": rec.get("title", ""),
        "creator": lab.get("creator", ""),
        "true_label": true_label,
        "mechanism": lab.get("mechanism", ""),
        "retrieved_policies": [
            {"category": h["record"]["category"], "score": round(h["score"], 3),
             "source_url": h["record"]["source_url"]} for h in hits],
        "verdict": parsed,
        "raw": None if parsed else raw[:500],
    }
    if parsed and expected:
        report["agree"] = (parsed["verdict"] == expected)
    return report, parsed, hits, true_label, expected, lab


def save_report(report, vid, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    name = (vid or "adhoc") + ".json"
    with open(os.path.join(out_dir, name), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    return os.path.join(out_dir, name)


def content_labelled_ids(labels, dataset_idx, prefixes):
    ids = []
    for vid, r in labels.items():
        mech = (r.get("mechanism", "") or "")
        if prefixes and not mech.startswith(prefixes):
            continue
        if vid not in dataset_idx:
            continue
        with open(dataset_idx[vid], encoding="utf-8") as fh:
            rec = json.load(fh)
        if (rec.get("transcript", "") or "").strip():
            ids.append(vid)
    return ids


def run_batch(args, vectors, records, labels, dataset_idx):
    import csv
    prefixes = tuple(p.strip() for p in args.mechanisms.split(",") if p.strip())
    ids = content_labelled_ids(labels, dataset_idx, prefixes)
    if not ids:
        sys.exit("no content-labelled videos with transcripts found")
    os.makedirs(args.out_dir, exist_ok=True)
    if getattr(args, "resume", False):
        done = {os.path.splitext(f)[0] for f in os.listdir(args.out_dir)
                if f.endswith(".json")}
        skipped = [v for v in ids if v in done]
        ids = [v for v in ids if v not in done]
        if skipped:
            print(f"resume: skipping {len(skipped)} already-saved report(s)")
    print(f"judging {len(ids)} labelled video(s) "
          f"(mechanism prefix: {','.join(prefixes) or 'any'})\n")
    if not ids:
        print("nothing left to judge.")
        return
    summary_path = os.path.join(args.out_dir, "summary.csv")
    fields = ["video_id", "creator", "true_label", "mechanism", "verdict",
              "agree", "risk", "confidence", "top_policy", "top_score",
              "reasoning"]
    n_agree = n_eval = 0
    rows = []
    for i, vid in enumerate(ids, 1):
        with open(dataset_idx[vid], encoding="utf-8") as fh:
            rec = json.load(fh)
        rec.setdefault("video_id", vid)
        try:
            report, parsed, hits, true_label, expected, lab = judge_video(
                rec, vid, vectors, records, labels, args)
        except Exception as e:
            print(f"[{i}/{len(ids)}] {vid} ERROR: {str(e)[:100]}")
            continue
        save_report(report, vid, args.out_dir)
        top = hits[0]["record"]["category"] if hits else ""
        top_score = round(hits[0]["score"], 3) if hits else ""
        agree = ""
        if parsed and expected:
            n_eval += 1
            agree = report.get("agree")
            if agree:
                n_agree += 1
        rows.append({
            "video_id": vid, "creator": lab.get("creator", ""),
            "true_label": true_label, "mechanism": lab.get("mechanism", ""),
            "verdict": parsed["verdict"] if parsed else "PARSE_FAIL",
            "agree": agree, "risk": parsed.get("risk", "") if parsed else "",
            "confidence": parsed.get("confidence", "") if parsed else "",
            "top_policy": top, "top_score": top_score,
            "reasoning": (parsed.get("overall_reasoning", "") if parsed else "")[:300],
        })
        v = parsed["verdict"].upper() if parsed else "PARSE_FAIL"
        flag = ""
        if parsed and expected:
            flag = "  <-- DIVERGENCE (over-enforcement)" if not report.get(
                "agree") else "  (agrees)"
        print(f"[{i}/{len(ids)}] {vid:16} true={true_label:11} "
              f"-> {v:11} (top: {top} {top_score}){flag}")
    with open(summary_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"\nagreement with creator labels: {n_agree}/{n_eval}"
          + (f" ({100.0*n_agree/n_eval:.0f}%)" if n_eval else "")
          + "   [small N -- read divergences as case studies]")
    print(f"-> {summary_path}")
    print(f"-> per-video reports in {args.out_dir}/")


def main():
    ap = argparse.ArgumentParser(
        description="Phase 2: transcript analyser. Retrieve the policy sections a "
                    "transcript actually touches (RAG), then have an open-source "
                    "Ollama model judge monetise/limited/demonetise with evidence, "
                    "policy grounding, and uncertainty.")
    ap.add_argument("--video-id", help="id present in data/dataset/<slug>/")
    ap.add_argument("--all", action="store_true",
                    help="judge every labelled video with a transcript and write "
                         "a summary table + agreement tally")
    ap.add_argument("--mechanisms", default="content",
                    help="in --all mode, only judge labels whose mechanism starts "
                         "with these (comma-sep); blank = all")
    ap.add_argument("--transcript-file", help="analyse a raw transcript file")
    ap.add_argument("--title", default="")
    ap.add_argument("--description", default="")
    ap.add_argument("--index", default=DEFAULT_INDEX)
    ap.add_argument("--meta", default=DEFAULT_META)
    ap.add_argument("--labels", default=DEFAULT_LABELS)
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--model", default=DEFAULT_CHAT_MODEL)
    ap.add_argument("--embed-model", default=DEFAULT_EMBED_MODEL)
    ap.add_argument("-k", type=int, default=5, help="policy sections to retrieve")
    ap.add_argument("--num-ctx", type=int, default=8192)
    ap.add_argument("--timeout", type=float, default=300.0)
    ap.add_argument("--out-dir", default=DEFAULT_OUT)
    ap.add_argument("--save", action="store_true", help="write the report json")
    ap.add_argument("--resume", action="store_true",
                    help="in --all mode, skip videos whose report json already "
                         "exists in out-dir")
    args = ap.parse_args()

    if not (os.path.exists(args.index) and os.path.exists(args.meta)):
        sys.exit("no policy index; run 'policy_rag.py build' first")
    vectors, records, _ = load_index(args.index, args.meta)
    dataset_idx = build_dataset_index()
    labels = load_labels(args.labels)

    if args.all:
        run_batch(args, vectors, records, labels, dataset_idx)
        return

    rec, vid = make_record(args, dataset_idx)
    report, parsed, hits, true_label, expected, lab = judge_video(
        rec, vid, vectors, records, labels, args)

    print("=" * 72)
    print(f"VIDEO: {rec.get('title','')[:70]}  ({vid or 'ad-hoc'})")
    if true_label:
        print(f"creator label: {true_label}  ({lab.get('mechanism','')})")
    print("retrieved policy areas:",
          ", ".join(f"{h['record']['category']} {h['score']:.2f}" for h in hits))
    print("-" * 72)
    if parsed:
        print(f"VERDICT: {parsed['verdict'].upper()}   "
              f"risk={parsed.get('risk','?')}   "
              f"confidence={parsed.get('confidence','?')}")
        if expected:
            print(f"agrees with creator label ({expected}): "
                  f"{parsed['verdict'] == expected}")
        for pa in parsed.get("policy_areas", []):
            print(f"\n  • {pa.get('category','?')} -> {pa.get('assessment','')}")
            if pa.get("evidence"):
                print(f"    evidence: {pa['evidence'][:200]}")
        print("\nreasoning:", parsed.get("overall_reasoning", ""))
    else:
        print("PARSE FAILED. raw head:", (report.get("raw") or "")[:300])

    if args.save:
        os.makedirs(args.out_dir, exist_ok=True)
        name = (vid or "adhoc") + ".json"
        with open(os.path.join(args.out_dir, name), "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=2)
        print(f"\n-> {os.path.join(args.out_dir, name)}")


if __name__ == "__main__":
    main()
