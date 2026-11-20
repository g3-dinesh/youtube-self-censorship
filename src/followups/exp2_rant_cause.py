"""#2 Post-mortem rant cause extraction (runs on server, localhost Ollama).

For each 'rant' transcript (creator explaining why they think they were
demonetised), ask qwen3 to extract the creator's ATTRIBUTED CAUSE and classify
it as a FOLK-type trigger (a specific word, swearing, first-30s, a short clip,
thumbnail/title) vs a POLICY-type category (sensitive event, controversial
issue, graphic content, repeated profanity) vs OTHER.

Output: out2.jsonl  {id, title, blamed_text, cause_type, cause_label, confidence}
"""
import json, os, sys, urllib.request

HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
MODEL = "qwen3:8b"
INP = sys.argv[1] if len(sys.argv) > 1 else "metadiscourse.jsonl"
OUT = sys.argv[2] if len(sys.argv) > 2 else "out2.jsonl"

SYS = ("You analyse YouTube creators' videos where they explain why they believe "
       "their video was demonetised / got the yellow dollar / limited ads. "
       "Extract what the CREATOR blames. Answer with ONE json object only.")
SCHEMA = """Respond with ONLY this JSON:
{
 "blamed_text": "<short quote/paraphrase of what the creator blames>",
 "cause_type": "folk" | "policy" | "other" | "none_stated",
 "cause_label": "<one of: specific_word, swearing, first_30_seconds, short_clip, thumbnail, title, topic_sensitive_event, topic_controversial, graphic_content, repeated_profanity, copyright, manual_review, unknown>",
 "confidence": "low"|"medium"|"high"
}
folk = creator blames a superstitious/lexical trigger (a single word, swearing,
       'first 30 seconds', a 3-second clip, the thumbnail/title).
policy = creator blames an actual advertiser-policy category (sensitive event,
         controversial issue, graphic content, sustained profanity)."""


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
    rants = [r for r in rows if r.get("type") == "rant"]
    done = set()
    if os.path.exists(OUT):
        for l in open(OUT, encoding="utf-8"):
            try: done.add(json.loads(l)["id"])
            except: pass
    fh = open(OUT, "a", encoding="utf-8")
    print(f"{len(rants)} rant transcripts ({len(done)} done)", flush=True)
    for i, r in enumerate(rants, 1):
        if r["id"] in done:
            continue
        tx = " ".join(str(r.get("transcript", "")).split())[:7000]
        prompt = f"TITLE: {r.get('title','')}\n\nTRANSCRIPT (truncated):\n{tx}\n\n{SCHEMA}"
        try:
            pv = parse(chat(prompt)) or {}
        except Exception as e:
            print(f"  [{i}] {r['id']} ERR {str(e)[:60]}", flush=True); continue
        rec = {"id": r["id"], "title": r.get("title", ""), "channel": r.get("channel", ""),
               "blamed_text": pv.get("blamed_text", ""), "cause_type": pv.get("cause_type", ""),
               "cause_label": pv.get("cause_label", ""), "confidence": pv.get("confidence", "")}
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n"); fh.flush()
        print(f"  [{i}/{len(rants)}] {rec['cause_type']:5} {rec['cause_label']}", flush=True)
    fh.close()
    print("DONE ->", OUT)


if __name__ == "__main__":
    main()
