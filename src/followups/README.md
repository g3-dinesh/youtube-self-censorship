# Follow-up experiments

Extensions to the core pipeline (`src/01`–`src/10`). They reuse the core
detector/lexicon via a thin shim (`casestudy_common.py` → `src/common.py`), so
they count things exactly the way the main pipeline does. Generated result files are written to
`outputs/followups/` (git-ignored); the written-up numbers live in
[`docs/RESULTS.md`](../../docs/RESULTS.md).

> **Corpus note.** The corpus-level scripts run on `data/master_transcripts.jsonl`,
> rebuilt locally by `build_master_corpus.py` from the full bundled corpus
> (`euph_transcripts.jsonl` + `dataset/`, **3,617 videos / 65 channels**). The
> numbers therefore reproduce the figures in `docs/RESULTS.md` exactly — e.g.
> detector 375 lexicon flags / 181 benign-prone, audience OR 1.50 [1.06, 2.37].
> The master file itself is regenerated rather than committed (it duplicates data
> already in the repo).

## Setup

```bash
pip install -r requirements.txt            # adds scipy + scikit-learn
python src/followups/build_master_corpus.py   # -> data/master_transcripts.jsonl
```

## The Talk-vs-Walk phenomenon (strongest contribution)

Creators are **policy-literate when they explain demonetisation** but act on
**inflated fear**. Three cohorts were collected and judged:

| Script | What it does | Needs |
|---|---|---|
| `scrape_advice.py` | collect "how to avoid demonetisation" advice videos | network |
| `scrape_rants.py` | collect "my channel got demonetised" post-mortems | network |
| `scrape_creator_talk.py` | find each behavioural creator's own demonetisation video | network |
| `scrape_interview_podcast.py` | collect interviews + main-vs-podcast channel pairs | network |
| `merge_metadiscourse.py` | merge the scraped cohorts into `data/metadiscourse.jsonl` | — |
| `exp1_advice_rules.py` | **#1** qwen3 extracts + classifies each stated rule (folk/policy/platform) | Ollama |
| `exp1_advice_lexical.py` | **#1** deterministic keyword twin of the above (no GPU) | — |
| `exp2_rant_cause.py` | **#2** qwen3 extracts the blamed cause from each rant | Ollama |
| `agg_advice_rules.py` | **#1** aggregate `out1.jsonl` → Folk-Theory Alignment table | — |
| `agg_rant_cause.py` | **#2** aggregate `out2.jsonl` → policy/folk table | — |
| `build_creator_talkwalk.py` | **#1b** pair each creator's talk folk-score vs validated masking rate | — |

## What self-censorship looks like / whether it works

| Script | Result | Needs |
|---|---|---|
| `exp3_podcast_delta.py` | **#3** within-creator main-vs-podcast register delta (profanity, algospeak) | — |
| `cs_leaky_proximity.py` | **leaky-mask proximity**: how far the plain word sits from the mask | — |
| `per_creator_masking.py` | per-creator masking rate over the master corpus (recall-heavy lexicon) | — |

## Measurement validity (#2, #4, #5)

| Script | Result | Needs |
|---|---|---|
| `cs_detector_compare.py` | **#4** strict vs lexicon detector: precision loss from benign-prone words | — |
| `cs_audience_controls.py` | **#5** audience mirroring survives creator fixed-effects logit + within-creator test | scipy, sklearn |
| `build_annotation_set.py` | **#2** build the 200-video human-validation sample (4 strata + IP weights) | — |
| `score_annotation.py` | **#2** Cohen's kappa + human-vs-System-A/B once two annotators label it | sklearn |

### Human-validation instrument (`data/annotation/`)
`build_annotation_set.py` writes `annotation_sample.csv` (blank, for two
annotators), `annotation_key.csv` (held-out machine verdicts), `annotation_strata.csv`
(population sizes + inverse-probability weights `w = N_h/n_h`), and
`ANNOTATION_GUIDE.txt`. After both annotators fill `a1_*`/`a2_*`,
`score_annotation.py` reports **Question A** (do humans see the gap? — unweighted
and population-weighted) and **Question B** (which system is closer to humans?),
stratified, with an error table. Two human annotators are the only manual step.
