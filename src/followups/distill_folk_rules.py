"""THE MIDDLE STEP: turn scraped Reddit posts into System B's folk-theory rules.

Pipeline:
  collect_reddit_demo.py   -> Reddit posts          (scrape)
  distill_folk_rules.py    -> canonical folk rules   (this script, qwen3 map-reduce)
  07_system_b_judge.py     -> verdicts               (loads the rules, judges videos)

Map:    qwen3 extracts each belief statement from batches of belief-bearing posts.
Reduce: qwen3 consolidates them into a de-duplicated, ranked list of folk rules.
Score:  each rule is weighted by how often its keywords appear in the corpus.

Reads the demo posts and writes a DEMO rule file to outputs/followups/ — it does
NOT overwrite the validated data/folk_corpus/folk_rules.json that ships with the
repo. Needs a running Ollama server (localhost by default; see README).

    python src/followups/distill_folk_rules.py                     # from the demo posts
    python src/followups/distill_folk_rules.py --in data/folk_corpus/reddit.jsonl
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))          # add src/ so the backend imports resolve
from policy_rag import DEFAULT_HOST                  # noqa: E402
import monetisation_judge as mj                      # noqa: E402

REPO = os.path.dirname(os.path.dirname(HERE))
OUTDIR = os.path.join(REPO, "outputs", "followups")
DEFAULT_IN = os.path.join(OUTDIR, "reddit_demo_posts.jsonl")
BELIEFS = os.path.join(OUTDIR, "beliefs_raw_demo.jsonl")
OUT_JSON = os.path.join(OUTDIR, "folk_rules_demo.json")
OUT_TXT = os.path.join(OUTDIR, "folk_rules_demo.txt")

BELIEF_PAT = re.compile(
    r"\b(if you|because|for saying|will get|gets you|get you|triggers?|as long as|"
    r"avoid|make sure|never say|rule of thumb|in my experience|learned that|turns "
    r"out|apparently|seems? like|i think|demonetiz|demonetis|advertiser|first \d+ "
    r"seconds?|age restrict|swear|reused|reaction|copyright|thumbnail)\b", re.I)

MAP_SYS = ("You extract CREATOR FOLK-THEORIES about YouTube demonetisation from "
           "forum text. A folk-theory is a creator's BELIEF about what causes a "
           "video/channel to be demonetised, limited, or age-restricted. Ignore "
           "generic venting, drama, and off-topic text. Output only JSON.")
MAP_SCHEMA = ('Return ONLY: {"beliefs":[{"belief":"<one-sentence rule creators '
              'believe>","topic":"<short tag e.g. profanity, copyright, reused, '
              'firearms, covid, thumbnail, ai, appeals>","quote":"<<=25-word '
              'supporting quote from the text>"}]}. Empty list if none.')
RED_SYS = ("You consolidate many raw creator folk-theory statements about YouTube "
           "demonetisation into a clean, de-duplicated, ranked list of distinct "
           "canonical rules. Merge duplicates. Output only JSON.")
RED_SCHEMA = ('Return ONLY: {"folk_rules":[{"rule":"<canonical one-sentence folk '
              'belief>","topic":"<short tag>","keywords":["<lowercase corpus '
              'keywords that indicate this rule>"],"example":"<one short quote>"}]}'
              '. Give 8-14 distinct rules, most common first.')


def post_text(r):
    # the demo scraper stores title + selftext; combine both as the belief text
    return (str(r.get("title", "")) + ". " + str(r.get("text", ""))).strip()


def load_snippets(path):
    out = []
    for line in open(path, encoding="utf-8"):
        try:
            r = json.loads(line)
        except Exception:
            continue
        t = post_text(r)
        if t and BELIEF_PAT.search(t):
            out.append(t[:600])
    return out


def batched(items, n):
    for i in range(0, len(items), n):
        yield items[i:i + n]


def main():
    ap = argparse.ArgumentParser(description="Distil scraped Reddit posts into folk rules (qwen3 map-reduce).")
    ap.add_argument("--in", dest="inp", default=DEFAULT_IN)
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--model", default=mj.DEFAULT_CHAT_MODEL)
    ap.add_argument("--batch", type=int, default=12)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--timeout", type=float, default=300.0)
    args = ap.parse_args()

    if not os.path.exists(args.inp):
        sys.exit(f"no input posts at {args.inp}\n-> run: python src/followups/collect_reddit_demo.py --limit 25")
    os.makedirs(OUTDIR, exist_ok=True)

    snippets = load_snippets(args.inp)
    if args.limit:
        snippets = snippets[:args.limit]
    print(f"belief-bearing snippets: {len(snippets)}")
    if not snippets:
        sys.exit("no belief-bearing posts found; scrape more with collect_reddit_demo.py --limit 25")

    # ---- MAP: extract beliefs from each batch ----
    batches = list(batched(snippets, args.batch))
    fh = open(BELIEFS, "w", encoding="utf-8")
    for bi, batch in enumerate(batches):
        text = "\n\n".join(f"[{j+1}] {s}" for j, s in enumerate(batch))
        prompt = "Extract creator folk-theories from these forum snippets.\n\n" + text + "\n\n" + MAP_SCHEMA
        try:
            raw = mj.call_chat(args.host, args.model, prompt, args.timeout, 8192, system=MAP_SYS, num_predict=1500)
            obj = json.loads(raw)
            for b in obj.get("beliefs", []):
                fh.write(json.dumps(b, ensure_ascii=False) + "\n")
            fh.flush()
            n = len(obj.get("beliefs", []))
        except Exception as e:
            n = -1
            print(f"  batch {bi} ERR {str(e)[:60]}")
        print(f"[map {bi+1}/{len(batches)}] +{n} beliefs", flush=True)
    fh.close()

    beliefs = []
    for line in open(BELIEFS, encoding="utf-8"):
        try:
            beliefs.append(json.loads(line))
        except Exception:
            pass
    print(f"\ntotal raw beliefs: {len(beliefs)}")
    if not beliefs:
        sys.exit("no beliefs extracted (is Ollama reachable? run: python check_ollama.py)")

    # ---- REDUCE: consolidate into canonical rules ----
    belief_lines = sorted({b.get("belief", "").strip() for b in beliefs if b.get("belief")})
    red_prompt = ("Consolidate these raw creator folk-theories into canonical rules.\n\n"
                  + "\n".join(f"- {b}" for b in belief_lines[:400]) + "\n\n" + RED_SCHEMA)
    raw = mj.call_chat(args.host, args.model, red_prompt, args.timeout, 8192, system=RED_SYS, num_predict=3000)
    rules = json.loads(raw).get("folk_rules", [])

    # ---- SCORE: weight each rule by keyword frequency in the corpus ----
    corpus_text = " ".join(post_text(json.loads(l)).lower()
                           for l in open(args.inp, encoding="utf-8") if l.strip())
    for r in rules:
        kws = [k.lower() for k in r.get("keywords", []) if k]
        r["support"] = sum(corpus_text.count(k) for k in kws)
    rules.sort(key=lambda r: r.get("support", 0), reverse=True)

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump({"n_snippets": len(snippets), "n_raw_beliefs": len(beliefs), "rules": rules},
                  f, ensure_ascii=False, indent=2)
    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write(f"EVIDENCE-GROUNDED CREATOR FOLK-THEORIES (DEMO)\n"
                f"(distilled from {len(snippets)} belief-bearing snippets, {len(beliefs)} raw beliefs)\n\n")
        for i, r in enumerate(rules, 1):
            f.write(f"{i}. [{r.get('topic','')}, ~{r.get('support',0)} corpus mentions] {r.get('rule','')}\n")
            if r.get("example"):
                f.write(f'     e.g. "{r["example"][:160]}"\n')

    print(f"\n{len(rules)} canonical folk rules -> {OUT_JSON}")
    print(f"-> {OUT_TXT}\n")
    for i, r in enumerate(rules, 1):
        print(f"{i:2}. [{r.get('topic',''):11} ~{r.get('support',0):4}] {r.get('rule','')[:80]}")
    print("\n(This DEMO file is separate from the validated data/folk_corpus/folk_rules.json")
    print(" that System B actually loads. It shows the scrape -> rules step end to end.)")


if __name__ == "__main__":
    main()
