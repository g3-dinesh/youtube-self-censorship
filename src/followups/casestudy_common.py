"""Compatibility shim for the follow-up experiment scripts.

These scripts were first written in the development repository, where they
imported a module called `casestudy_common`. In this (clean) repository the
shared masking detector and lexicon live in `src/common.py`, so this shim
re-exports them under the old name and adds an outputs directory for the
generated CSV/TXT result files. Nothing here changes behaviour.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))  # add src/ so `import common` resolves
import common as _c  # noqa: E402

REPO = os.path.dirname(os.path.dirname(_HERE))          # repository root
BLEEP = _c.BLEEP                                         # bleep / [__] regex
DIGIT_MASK = _c.DIGIT_MASK                               # letter/digit-mask regex
load_lexicon = _c.load_lexicon                           # curated euphemism lexicon
DATASET = _c.DATASET                                     # data/dataset
CS = CH = os.path.join(REPO, "outputs", "followups")     # where results are written
os.makedirs(CS, exist_ok=True)
