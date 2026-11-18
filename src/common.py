"""Shared toolkit used by several scripts in this project.

Holds the ONE deterministic masking detector, the curated euphemism lexicon,
the dataset loader, and small stats helpers (percentages, Wilson confidence
intervals). Keeping these in one place means every analysis counts masking the
exact same way, so results are comparable across scripts.

Paths are resolved relative to this file, so the repo runs from anywhere after
`git clone` — nothing is hard-coded to one machine.
"""
import csv, glob, json, math, os, re
from datetime import date

# repo root = the folder that contains src/ and data/
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DATASET = os.path.join(REPO, "data", "dataset")
OUT = os.path.join(REPO, "outputs")
LEXICON_CSV = os.path.join(REPO, "data", "self_censorship_lexicon_curated.csv")
os.makedirs(OUT, exist_ok=True)

# colour-blind-safe palette (Okabe-Ito), used in every chart so figures match
BLUE, ORANGE, GREEN, VERM, PURPLE, INK, GRID = (
    "#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#1a1a1a", "#d9d9d9")

# --- the validated ~100%-precision masking detector ------------------------
# BLEEP matches explicit censor markers: [ __ ], [bleep], *bleep*, [censored].
BLEEP = re.compile(
    r"\[\s*_+\s*\]|\[\s*bleep\s*\]|\(\s*bleep\s*\)|\*bleep\*|\[\s*censored\s*\]|\bbleep(?:ed)?\b",
    re.I)
# DIGIT_MASK matches letter-swapped / euphemised sensitive words.
DIGIT_MASK = re.compile(
    r"\b(?:sh[1!]t|f[4@]ck|ph[u4]ck|b[1!]tch|d[1!]ck|f+ck|btch|f[-_]?word|"
    r"n[- ]?word|s[- ]?word|unalive|sewer\s*slide|grape)\b", re.I)


def masked(tx):
    """True if the transcript contains any masking/euphemism marker."""
    tx = tx or ""
    return bool(BLEEP.search(tx) or DIGIT_MASK.search(tx))


def mask_count(tx):
    """How many masking markers the transcript contains."""
    tx = tx or ""
    return len(BLEEP.findall(tx)) + len(DIGIT_MASK.findall(tx))


def load_lexicon():
    """Curated euphemism terms marked KEPT by manual review, as compiled regexes."""
    lex = []
    if not os.path.exists(LEXICON_CSV):
        return lex
    for x in csv.DictReader(open(LEXICON_CSV, encoding="utf-8-sig")):
        if x.get("curation_decision", "").upper() == "KEPT":
            t = x["term"].lower()
            lex.append((t, re.compile(r"(?<![a-z])" + re.escape(t) + r"(?![a-z])")))
    return lex


def pct(k, n):
    return round(100 * k / n, 1) if n else 0.0


def wilson(k, n, z=1.96):
    """95% Wilson score interval for a proportion -> (point%, low%, high%)."""
    if n == 0:
        return (0.0, 0.0, 0.0)
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / den
    return (round(100 * p, 1), round(100 * max(0, c - h), 1),
            round(100 * min(1, c + h), 1))


def to_ord(d):
    """YYYYMMDD -> ordinal day number (for date arithmetic)."""
    d = str(d)
    return date(int(d[:4]), int(d[4:6]), int(d[6:8])).toordinal()


def quarter(d):
    """YYYYMMDD -> 'YYYYQn'."""
    d = str(d)
    return f"{d[:4]}Q{(int(d[4:6]) - 1) // 3 + 1}"


def load_videos(require_transcript=True):
    """Yield one normalised record per dataset video (data/dataset/<creator>/*.json)."""
    for f in glob.glob(os.path.join(DATASET, "*", "*.json")):
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        u = str(d.get("upload_date") or "")
        if len(u) != 8 or not u.isdigit():
            continue
        tx = d.get("transcript") or ""
        if require_transcript and len(str(tx).split()) < 50:
            continue
        slug = d.get("slug") or os.path.basename(os.path.dirname(f))
        yield {
            "slug": slug, "id": d.get("id"), "date": u,
            "title": d.get("title") or "", "transcript": tx,
            "n_words": len(str(tx).split()),
            "view_count": d.get("view_count") or 0,
            "masked": masked(tx), "mask_count": mask_count(tx),
        }
