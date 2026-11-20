"""#3 Podcast-vs-Main (lighter form): within-creator register delta.

NOT same-topic matched. Measures, per creator, whether the podcast/2nd channel
uses MORE raw language (profanity) and LESS algospeak/euphemism than the main
channel - i.e. is the main channel where self-censorship concentrates?

Metrics per 100 words:
  profanity   (uncensored strong words)
  algospeak   (unalive, grape, seggs, etc. - the euphemisms)
  explicit    (plain sensitive words: kill, death, sex, suicide, rape...)
Reports per-creator role means + delta (podcast - main) + video-level bootstrap.
"""
import json, os, re, collections, random
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INP = os.path.join(REPO, "data", "podcast_pairs.jsonl")
OUT = os.path.join(REPO, "outputs", "followups", "Results_Exp3_PodcastDelta.txt")

PROFANITY = re.compile(r"\b(fuck\w*|shit\w*|bitch\w*|asshole|dick\w*|cunt|motherf\w*|"
                       r"bullshit|goddamn|pissed|cock|whore|slut)\b", re.I)
ALGOSPEAK = re.compile(r"\b(unalive\w*|un[- ]?alive|grape\w*|seggs|segg|corn\b|le[$s]bian|"
                       r"cheese pizza|pdf file|accountant|unoalive|sewerslide|"
                       r"k[i1!]ll(?:ed|ing)?(?=\s|$)|d[i1!]e\b|dead\b)\b", re.I)
EXPLICIT = re.compile(r"\b(kill\w*|murder\w*|death|dead|died|suicide|rape\w*|sex\w*|"
                      r"drug\w*|gun\w*|shoot\w*|abuse\w*|assault\w*|porn\w*|nazi|terroris\w*)\b", re.I)


def per100(text, rx):
    w = max(1, len(text.split()))
    return 100.0 * len(rx.findall(text)) / w


def boot_ci(vals, n=4000):
    if len(vals) < 2:
        return (float("nan"), float("nan"))
    out = []
    for _ in range(n):
        s = [random.choice(vals) for _ in vals]
        out.append(sum(s) / len(s))
    out.sort()
    return out[int(.025 * n)], out[int(.975 * n)]


def main():
    random.seed(7)
    rows = [json.loads(l) for l in open(INP, encoding="utf-8") if l.strip()]
    by = collections.defaultdict(lambda: collections.defaultdict(list))  # creator->role->list of per-video metric dicts
    for r in rows:
        tx = r.get("transcript", "")
        if len(tx.split()) < 150:
            continue
        by[r["creator"]][r["role"]].append({
            "prof": per100(tx, PROFANITY),
            "algo": per100(tx, ALGOSPEAK),
            "expl": per100(tx, EXPLICIT),
            "words": len(tx.split()),
        })

    lines = []
    lines.append("=" * 74)
    lines.append("EXPERIMENT #3  -  PODCAST vs MAIN CHANNEL  (within-creator register delta)")
    lines.append("=" * 74)
    lines.append("LIGHTER FORM: within-creator format comparison, NOT same-topic matched.")
    lines.append("Positive delta = podcast channel has MORE of that feature than main.\n")

    for creator in sorted(by):
        roles = by[creator]
        if "main" not in roles or "podcast" not in roles:
            have = ",".join(f"{k}={len(v)}" for k, v in roles.items())
            lines.append(f"[{creator}] SKIPPED - need both roles (have {have})")
            continue
        lines.append(f"[{creator}]  main n={len(roles['main'])}  podcast n={len(roles['podcast'])}")
        for metric, lab in [("prof", "profanity"), ("algo", "algospeak/euphem"), ("expl", "explicit-sensitive")]:
            mv = [v[metric] for v in roles["main"]]
            pv = [v[metric] for v in roles["podcast"]]
            mm = sum(mv) / len(mv); pm = sum(pv) / len(pv)
            delta = pm - mm
            lo, hi = boot_ci([x - mm for x in pv])  # CI of podcast mean recentred - rough
            sig = "SIG" if (lo > 0 or hi < 0) else "ns "
            lines.append(f"   {lab:18} main {mm:6.3f}/100w   podcast {pm:6.3f}/100w   "
                         f"delta {delta:+6.3f}  [{sig}]  CI[{lo:+.3f},{hi:+.3f}]")
        lines.append("")

    lines.append("INTERPRETATION")
    lines.append("  profanity delta > 0  : podcast is the LOOSER register (main is where")
    lines.append("                          the creator cleans up = self-censorship venue).")
    lines.append("  algospeak delta < 0  : podcast drops the euphemisms (says plain words).")
    lines.append("  CAVEAT: single-creator pair(s), not topic-matched. This is a format-")
    lines.append("  register signal, NOT proof of topic-controlled censorship. Descriptive.")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write("\n".join(lines))
    print("\n".join(lines))
    print("\n-> saved", OUT)


if __name__ == "__main__":
    main()
