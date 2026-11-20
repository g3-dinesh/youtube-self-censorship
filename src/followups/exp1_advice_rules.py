"""#1 Walk-vs-Talk: extract STATED self-censorship rules from advice videos.

Advice videos = creators telling others how to stay monetised. For each, qwen3
extracts every concrete STATED RULE ("don't say X", "cut swearing in first 30s",
"never show a gun") and classifies each as:
  folk    = superstitious/lexical ritual (a specific banned word, swearing per se,
            'first 30 seconds', thumbnail magic, a 3-second clip, say 'unalive')
  policy  = a real advertiser-guideline category (controversial social issues,
            graphic violence, sexual content, sustained/gratuitous profanity,
            hateful content, dangerous acts, shocking content)
  platform= a true platform mechanic (self-certification questionnaire, appeal,
            manual review, limited-ads state) stated accurately
  other / unclear

Output: out1.jsonl {id, title, channel, n_rules, rules:[{rule,type,word?}], folk, policy, platform}
Aggregate (computed separately): Folk-Theory Alignment = folk / (folk+policy).
"""
import json, os, sys, urllib.request

HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
MODEL = "qwen3:8b"
INP = sys.argv[1] if len(sys.argv) > 1 else "metadiscourse.jsonl"
OUT = sys.argv[2] if len(sys.argv) > 2 else "out1.jsonl"

SYS = ("You analyse YouTube creator ADVICE videos about staying monetised / avoiding "
       "demonetisation. Extract every CONCRETE RULE the speaker tells viewers to follow. "
       "Ignore vague motivation. Output ONE json object only, no prose.")
SCHEMA = """Respond with ONLY this JSON:
{
 "rules": [
   {"rule": "<short paraphrase of the stated rule>",
    "type": "folk" | "policy" | "platform" | "other",
    "trigger_word": "<the specific word/phrase if the rule is about a particular word, else ''>"}
 ]
}
Definitions:
 folk    = a superstitious or purely-lexical ritual: avoid one specific word, swearing
           in itself triggers demonetisation, 'the first 30 seconds / 15 seconds matter',
           thumbnail/title keywords cause it, a 3-second clip, you must say 'unalive'/'grape'
           /algospeak, censor-bleep every swear, mute a word.
 policy  = a genuine advertiser-guideline CATEGORY: controversial social/political issues,
           graphic violence or injury, sexual content, sustained/gratuitous profanity,
           hateful or derogatory content, dangerous/harmful acts, shocking content, firearms
           in harmful context, drugs.
 platform= an accurate platform mechanic: fill self-certification honestly, use the appeal
           button, wait out manual review, 'limited ads' is an ad-suitability state.
 other   = anything else (SEO, upload time, thumbnails-for-CTR, general 'make good content').
If the video states no concrete rule, return {"rules": []}."""


def chat(prompt):
    body = {"model": MODEL, "messages": [{"role": "system", "content": SYS},
            {"role": "user", "content": prompt}], "stream": False,
            "options": {"temperature": 0, "num_ctx": 8192}}
    req = urllib.request.Request(HOST + "/api/chat",
                                 data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    raw = urllib.request.urlopen(req, timeout=300).read().decode("utf-8", "replace")
    return json.loads(raw).get("message", {}).get("content", "")


def parse(s):
    i, j = s.find("{"), s.rfind("}")
    if i < 0 or j < 0:
        return None
    try:
        return json.loads(s[i:j + 1])
    except Exception:
        return None


def main():
    rows = [json.loads(l) for l in open(INP, encoding="utf-8") if l.strip()]
    adv = [r for r in rows if r.get("type") == "advice"]
    done = set()
    if os.path.exists(OUT):
        for l in open(OUT, encoding="utf-8"):
            try: done.add(json.loads(l)["id"])
            except: pass
    fh = open(OUT, "a", encoding="utf-8")
    print(f"{len(adv)} advice videos ({len(done)} done)", flush=True)
    for i, r in enumerate(adv, 1):
        if r["id"] in done:
            continue
        tx = " ".join(str(r.get("transcript", "")).split())[:7500]
        prompt = f"TITLE: {r.get('title','')}\n\nTRANSCRIPT (truncated):\n{tx}\n\n{SCHEMA}"
        try:
            pv = parse(chat(prompt)) or {}
        except Exception as e:
            print(f"  [{i}] {r['id']} ERR {str(e)[:60]}", flush=True); continue
        rules = pv.get("rules", []) or []
        cnt = {"folk": 0, "policy": 0, "platform": 0, "other": 0}
        for rl in rules:
            t = rl.get("type", "other")
            cnt[t if t in cnt else "other"] += 1
        rec = {"id": r["id"], "title": r.get("title", ""), "channel": r.get("channel", ""),
               "n_rules": len(rules), "rules": rules,
               "folk": cnt["folk"], "policy": cnt["policy"],
               "platform": cnt["platform"], "other": cnt["other"]}
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n"); fh.flush()
        print(f"  [{i}/{len(adv)}] rules={len(rules):2} folk={cnt['folk']} policy={cnt['policy']} platform={cnt['platform']}", flush=True)
    fh.close()
    print("DONE ->", OUT)


if __name__ == "__main__":
    main()
