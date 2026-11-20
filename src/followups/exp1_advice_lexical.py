"""#1 (deterministic, outage-proof): folk vs policy framing in ADVICE transcripts.

For each 'how to avoid demonetisation' advice video, count mentions of:
  FOLK markers   = lexical/ritual beliefs (a specific banned word, swearing per se,
                   'first N seconds', say 'unalive'/algospeak, bleep/mute words,
                   thumbnail/title magic, 3-second clip).
  POLICY markers = real advertiser-guideline categories (controversial issues,
                   graphic violence, sexual content, hate, drugs, sustained profanity,
                   'advertiser-friendly guidelines', self-certification).
Reports, across the advice (TALK) corpus, how folk-loaded the stated advice is.
This is the deterministic twin of the qwen3 rule-extractor (runs with no server).
"""
import json, os, re, collections
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INP = os.path.join(REPO, "data", "metadiscourse.jsonl")
OUT = os.path.join(REPO, "outputs", "followups", "Results_Exp1_AdviceFraming_lexical.txt")

FOLK = {
    "first_N_seconds": re.compile(r"\bfirst\s+(?:\d+|thirty|fifteen|ten|five)\s+seconds?\b", re.I),
    "specific_word_ban": re.compile(r"\b(can'?t say|don'?t say|never say|avoid saying|the word|certain words|"
                                    r"trigger words?|banned words?|flagged words?)\b", re.I),
    "swearing_per_se": re.compile(r"\b(swear\w*|curse words?|cuss\w*|cursing|bleep\w*|censor the|mute the word|"
                                  r"beep out)\b", re.I),
    "algospeak": re.compile(r"\b(unalive\w*|algospeak|say 'grape'|seggs|say instead|code words?)\b", re.I),
    "thumbnail_title_magic": re.compile(r"\b(thumbnail|in the title|clickbait|title and thumbnail)\b", re.I),
    "short_clip": re.compile(r"\b(\d+[- ]second clip|three second|3 second|a single frame|one frame)\b", re.I),
}
POLICY = {
    "controversial_issues": re.compile(r"\b(controvers\w*|sensitive topic\w*|sensitive event\w*|"
                                       r"social issue\w*|political)\b", re.I),
    "graphic_violence": re.compile(r"\b(graphic|violence|violent|gore|blood\w*|injury|injuries)\b", re.I),
    "sexual": re.compile(r"\b(sexual\w*|nudity|nude|adult content|porn\w*)\b", re.I),
    "hate_harm": re.compile(r"\b(hate\w*|harass\w*|discriminat\w*|dangerous|harmful|drug\w*|firearm\w*|weapon\w*)\b", re.I),
    "sustained_profanity": re.compile(r"\b(excessive profanity|gratuitous|throughout the video|repeated\w*|frequent\w*)\b", re.I),
    "official_guidelines": re.compile(r"\b(advertiser[- ]?friendly guidelines?|community guidelines?|"
                                      r"self[- ]?certif\w*|monetization polic\w*|ad[- ]?suitabilit\w*|"
                                      r"content rating)\b", re.I),
}


def main():
    rows = [json.loads(l) for l in open(INP, encoding="utf-8") if l.strip()]
    adv = [r for r in rows if r.get("type") == "advice"]
    folk_vid = collections.Counter(); policy_vid = collections.Counter()
    folk_hits_tot = policy_hits_tot = 0
    per = []
    for r in adv:
        tx = r.get("transcript", "") or ""
        fh = {k: len(rx.findall(tx)) for k, rx in FOLK.items()}
        ph = {k: len(rx.findall(tx)) for k, rx in POLICY.items()}
        f = sum(fh.values()); p = sum(ph.values())
        folk_hits_tot += f; policy_hits_tot += p
        for k, v in fh.items():
            if v: folk_vid[k] += 1
        for k, v in ph.items():
            if v: policy_vid[k] += 1
        per.append((r.get("title", "")[:48], f, p))

    n = len(adv)
    lines = []
    lines.append("=" * 74)
    lines.append("EXPERIMENT #1 (lexical twin)  -  FOLK vs POLICY FRAMING IN ADVICE VIDEOS")
    lines.append("=" * 74)
    lines.append(f"advice videos analysed : {n}   (the 'talk' corpus - stated rules)")
    lines.append(f"total folk-marker hits : {folk_hits_tot}")
    lines.append(f"total policy-marker hits: {policy_hits_tot}")
    tot = folk_hits_tot + policy_hits_tot
    if tot:
        lines.append(f"FOLK LOADING (folk / folk+policy mentions): {100*folk_hits_tot/tot:.1f}%")
    lines.append("")
    lines.append("--- FOLK markers: # of advice videos that mention each ---")
    for k in FOLK:
        lines.append(f"   {k:22} {folk_vid[k]:3}/{n}  ({100*folk_vid[k]/n:.0f}%)")
    lines.append("--- POLICY markers: # of advice videos that mention each ---")
    for k in POLICY:
        lines.append(f"   {k:22} {policy_vid[k]:3}/{n}  ({100*policy_vid[k]/n:.0f}%)")
    lines.append("")
    # how many videos are folk-dominant vs policy-dominant
    folk_dom = sum(1 for _, f, p in per if f > p)
    pol_dom = sum(1 for _, f, p in per if p > f)
    tie = sum(1 for _, f, p in per if p == f)
    lines.append(f"videos folk-dominant : {folk_dom}/{n}")
    lines.append(f"videos policy-dominant: {pol_dom}/{n}")
    lines.append(f"videos tied/empty    : {tie}/{n}")
    lines.append("")
    lines.append("INTERPRETATION")
    lines.append("  High folk loading = the advice creators give each other is framed around")
    lines.append("  lexical rituals (specific words, 'first 30s', bleeping) more than around")
    lines.append("  the actual advertiser-guideline CATEGORIES. That is the folk theory being")
    lines.append("  transmitted creator-to-creator - the 'talk' half of walk-vs-talk.")
    lines.append("  CAVEAT: deterministic keyword proxy; the qwen3 rule-extractor (server)")
    lines.append("  gives the per-rule classification. Mention counts != belief strength.")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write("\n".join(lines))
    print("\n".join(lines))
    print("\n-> saved", OUT)


if __name__ == "__main__":
    main()
