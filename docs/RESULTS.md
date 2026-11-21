# Investigating YouTube Self-Censorship Practices — Consolidated Results

**MSc research project · Gayathri Dinesh · compiled 2026-11-20**

This document consolidates every experiment in the project with its hypothesis,
method, corpus, numbers, verdict, and caveats. Results are grouped by the
argument they support. Nothing here is speculative — every number traces to a
saved analysis file named in its entry.

---

## The thesis in one paragraph

Self-censorship on YouTube is governed by **creator belief, not actual platform
policy**. Creators over-estimate their demonetisation risk by roughly **4×**, and
that fear produces real but *misdirected* behaviour. Crucially, the belief splits
into two layers that behave differently: when creators **talk** about
demonetisation (advice videos, post-mortem rants) they are **policy-literate**
(~87%); yet what they **fear** (System B perceived risk) is inflated ~4×. The gap
is between what they *know* and what they *fear*, not between their words and their
behaviour — a creator-level test finds matchable creators are *consistent*, so the
dissociation is perception-level. Observable self-censorship is therefore **light,
syntactic, and concentrated in packaging/framing** — not the heavy word-scrubbing
the folk theory would predict. It persists because it is a *habit of propriety*,
not a working evasion of any filter.

---

## PART I — The central result: belief ≠ reality

### Headline — the 4× perception gap
*(results/01_headline_perception_gap.csv; results/01_headline_1000videos_A_B_ad.csv)*

Two independent LLM judges rated a random 1,000-video sample:
- **System A** judges against YouTube's *actual* advertiser-friendly policy (RAG over the policy corpus).
- **System B** judges against creators' *folk theory* of what gets demonetised.

| Judge | "Would be demonetised" | 95% CI |
|---|---|---|
| System A (real policy) | **19.2%** | [16.9, 21.8] |
| System B (creator belief) | **75.6%** | [72.8, 78.2] |

A **56-point, 3.9× gap**; the CIs do not overlap. The two systems agree on only
42% of videos. Of the 808 videos policy says are perfectly fine, creators still
expect **70%** to be demonetised. This is the project's central, defensible result.

### Misdirected self-censorship — the hard-ground-truth version
*(results/02_misdirected_601_ads.csv)*

Restricting to **601 videos literally serving ads right now** (an ad serving
*proves* monetisation — the one-directional rule, no inference):
- Creator folk belief (System B): **76%** "would be demonetised."
- Written policy (System A): **17%**.

Creators self-censor content that is **demonstrably making money**. Because the
monetisation label here is hard ground truth, this is the strongest form of the
gap.

### Topic concentration
*(results/03_topic_concentration_A_vs_B.csv)*

On a curated topic-shift set, System B was stricter than System A on **9 of 11**
topics. Policy would monetise non-graphic commentary on Trump, abortion, COVID,
immigration; creators expect all of them demonetised. The fear concentrates on
hot-button political/health topics that policy actually permits.

---

## PART II — Walk-vs-Talk: the belief has two layers *(this session's new work)*

The sharpest finding of the final phase. The explicit/verbal layer and the
reflexive/behavioural layer disagree with each other.

### #1 — The "TALK": stated rules in advice videos
*(results/04_talk_advice_rules.csv; results/04_talk_advice_alignment.csv)*

**Cohort:** 19 "how to avoid demonetisation / words you can't say" advice videos —
creators' explicit public model of the rules.

**Method:** qwen3:8b extracts every concrete stated rule and classifies it
folk / policy / platform / other; a deterministic keyword twin cross-checks.

| Rule type (qwen3, 130 rules) | Count | Share |
|---|---|---|
| folk (ritual/lexical) | 9 | 6.9% |
| policy (real category) | 63 | 48.5% |
| platform (true mechanic) | 53 | 40.8% |
| other | 5 | 3.8% |

**Folk-Theory Alignment = folk/(folk+policy) = 12.5%.** 14/19 videos
policy-dominant, 1/19 folk-dominant. Lexical twin agrees: **15.9%** folk loading.

**Verdict:** ~87% of stated advice references genuine guideline categories or true
platform mechanics. When creators *talk*, they are policy-literate.

### #2 — The retrospective story: what rants blame
*(results/05_talk_rant_causes.csv; results/05_talk_rant_top_blame.csv)*

**Cohort:** 62 "my channel got demonetised" post-mortems (2 supplied playlists +
8 searches). qwen3 extracts the blamed cause.

| Blamed cause | Count | Share |
|---|---|---|
| policy category | 48 | 77% |
| folk ritual | 9 | 15% |
| other / none stated | 5 | 8% |

Top blame: sensitive event (17), controversial topic (14), copyright (6). The
retrospective account is also policy-grounded.

### The behavioural layer — the "WALK"
From across the project: the reflexive in-video behaviour is **folk-driven**:
- 76% folk-flag vs 17% policy on monetised videos (Part I).
- Masking concentrates in policy gray zones (#7 below).
- Appeals believed futile 8:1 despite policy (Part IV).

### The dissociation — and an honest correction on its *level*
| Layer | Register | Folk share |
|---|---|---|
| Talk — advice videos (#1) | explicit, prospective | ~12% |
| Talk — rants (#2) | explicit, retrospective | 15% |
| **Walk — perceived risk (System B)** | implicit, in-the-moment | **76% fear** |

**Creators know the policy when they explain it, yet *fear* far more than it
implies.** But a creator-level test (below) shows this is a **perception-level**
dissociation, not a within-creator "talks policy / scrubs words" effect.

### Creator-level Talk-vs-Walk
*(results/06_creator_level_talk_vs_walk.csv)*

We matched creators present in **both** a demonetisation talk-video **and** the
behavioural corpus (with a validated masking rate). Advice-channel creators
(vidIQ, TubeBuddy…) don't make sensitive content, so we reversed the design and
found each behavioural creator's own demonetisation video. **5 commentary
creators matched:**

| Creator | Talk folk-loading | Walk masking (validated) |
|---|---|---|
| Steven Crowder | 25% | 2.6% |
| Philip DeFranco | 0% | 1.4% |
| Kyle Kulinski | 0% | 1.1% |
| Tim Pool | 0% | 1.3% |
| David Pakman | 0% | 0.0% |

**All five are internally *consistent*** — policy-literate talk *and* low masking.
They are not the dissociated case. The heavy maskers (Kurtis Conner, CoryxKenshin,
true-crime/essay creators) **don't publish demonetisation talk-videos**, so the
within-creator dissociation cannot be tested on them.

**Honest conclusion:** the dissociation is between what creators **know/say**
(policy-literate) and what they **fear** (System B, inflated) — *not* between
their words and their word-scrubbing. Masking is a light, minority stylistic
reflex regardless of stated belief. The problem is a **fear calibration** problem,
not a knowledge gap. *(n=5, selected; downgraded from headline to robustness
note accordingly.)*

---

## PART III — What self-censorship actually looks like (the positive signals)

### Shield #1 — Packaging (title sanitisation)
*(results/07_shields_packaging_framing.csv; master corpus, 3,617 videos)*

Of 2,811 videos with explicitly sensitive transcripts, the **title is benign in
92.9%** [91.9, 93.8] — only 7.1% carry an explicit sensitive word in the title.
Creators routinely wrap sensitive content in a clean title. **This is the single
largest observable self-censorship behaviour.**

### Shield #3 — Framing over lexicon
*(results/07_shields_packaging_framing.csv)*

Creators lean on **explicit-word + context framing** (414 videos) far more than on
euphemism-without-framing (111) — a **3.7×** preference. They say the real word but
cushion it with documentary/educational context rather than coding it.

### Register shift — passive voice (Exp B & C)
*(results/08_register_passive_voice.csv)*

Within the same video, sensitive segments use **+0.103 passive verbs /100w**
[0.070, 0.135] more than that video's non-sensitive segments. At the creator level
(58 creators, creator-clustered bootstrap) the effect survives: **+0.099 /100w**
[0.065, 0.133], 45/58 creators positive, robust to excluding the top maskers.
Sensitive content shifts to a **more passive/formal register** — modest but real.

### Algospeak caught in the wild (hand-validated)
*(results/09_algospeak_validation_sample.csv)*

Real coded swaps, manually verified: *the vid* → covid · *grape* → rape · *cheeto*
→ Trump · *unalive* → kill · *pdf file* → pedophile · *yahtzee* → nazi. Sparse but
real — the mechanism exists.

---

## PART IV — What self-censorship is NOT (the nulls)

These are deliberate, honest negatives. Each kills a plausible stronger claim and
collectively they show the behaviour is light and non-strategic.

| # | Hypothesis tested | Result | Numbers |
|---|---|---|---|
| Exp B | Sensitive segments get vaguer (specificity substitution) | **NULL** | spec diff +0.083, CI crosses 0; passive the only exception |
| Exp C | Creators hide *who did it* (agent omission) | **NULL** | −0.007 rate, wrong direction, collapses excl. top maskers; abs 0.910 vs 0.917 |
| #2 shield | Sponsored videos use more guarded language than AdSense | **NULL** | mask 2.5% vs 2.5% = 1.01× |
| #4 | Captions mismatch the spoken track | **NULL** | 0/39 |
| #5B | Creators suppress sensitive words in comments | **NULL (reversed)** | high-risk comments MORE explicit (8.4% vs 3.0%) |
| #6 | Post-upload title scrubbing (shadow-edit) | **NULL** | 22/46 titles changed, 0 toward sanitised |
| Leaky mask | Masking is functional keyword evasion | **NULL** | 80% of masked videos also say the plain word; same ad rate 62% vs 59% |
| Counterfactual | Algospeak fools the policy judge | **Backfires** | algospeak 47%→57% not-monetised; disclaimer helps →23%; folk immune ~90% |
| Case studies | Policy/news/enforcement/sponsorship raise masking | **NULL ×4** | no consistent masking rise around any external pressure |

**The leaky mask (results/11_leaky_mask_proximity.csv)** is the most telling: a within-video
result (immune to creator/topic/time confounds) showing creators mask a word and
also say it plainly in the same video. **Proximity refinement (#3,
results/11_leaky_mask_proximity.csv):** when a mask "leaks," the plain word sits a
**median ~300 words (~2 min) away**; only **28–38% of leaks are local** (same
sentence / ~30s) and just **4–7% are same-breath**. So it is **not** emphatic
self-correction ("f***, I mean fuck") — masking flips on and off by *momentary
context* within a video, a local reflex rather than whole-video word-avoidance.
(n=29 leak tokens — small; directional.)

**The counterfactual (results/12_counterfactual_algospeak.csv)** is the only true
controlled experiment: changing only the wording, algospeak actually *raises* the
policy judge's demonetise rate (it reads as evasion), while a documentary
disclaimer lowers it — the ritual is aimed at the wrong lever.

---

## PART V — Dynamics, timing, and robustness

### #7 — Policy ambiguity zones
*(results/13_policy_ambiguity_zones.csv)*

System A run K=5× at temp 0.7 on 216 transcripts; ambiguity = entropy over the 5
verdicts. **43.1%** of videos make the policy judge *waver* across identical runs —
the policy boundary is genuinely fuzzy. Masking concentrates in these gray zones
(ambiguity 0.353 masked vs 0.217 unmasked, significant; sensitive-topic 0.267 vs
0.162, significant). **Creators ritualise precisely where the real rule is
unknowable** — a rational root for an irrational habit.

### #4 — Telephone-game drift
*(results/14_telephone_game_drift.csv)*

Folk-marker density in creator discourse vs official policy videos: **38.5×** more
folk-loaded (18% vs 5% use a superstitious marker) — but **p=0.18, not
significant** (folk markers are rare, concentrated in a minority). Directional
drift, not wholesale distortion.

### Self-censorship is a personal fingerprint
*(results/15_creator_fingerprint_timeline.csv)*

Masking is stable *per creator* across a decade — one creator masks ~100% of
videos, another ~0%, each steady cycle after cycle. It's a production habit baked
into style, not a response to events. 16/30 creators never mask.

### Contagion is in the vocabulary, but timing is null

Specific euphemisms (grape, unalive, cheeto) spread cross-genre across creators in
S-curves — governance-by-vocabulary-contagion. **But** Reddit demonetisation-anxiety
does **not** precede creator masking (dated archive, 28 quarters, 1,189 dated
videos, corrected **p=0.85**). The belief is shared, but there's no lead-lag
"panic → censor" cycle. A converging null that strengthens the belief-as-reflex
reading.

---

## PART VI — The audience shares the belief
*(results/16_audience_mirroring_controls.csv)*

Across **314,705 comments** on 1,532 videos: viewers use algospeak themselves
(~28%), openly discuss demonetisation (~10%), and mirror the creator's masking
(38% when the creator masks vs 23% when not). Self-censorship is a **community-wide
understanding**, not a creator tic.

**Does mirroring survive controls? (#5, cs_audience_controls.csv)** Yes, in the
regression. A **creator fixed-effects logistic regression** (adjusting for
sensitive-topic density, comment count, transcript length) gives the creator-masks
effect an **odds ratio of 1.50, 95% CI [1.06, 2.37]** — the CI excludes 1, so
mirroring is not merely a creator/topic artifact. A stricter **within-creator
paired test** (14 creators with both masked and unmasked videos) is directionally
positive (+5.5pp, 10/14 creators) but only **borderline significant (Wilcoxon
p=0.055)**. Honest read: the regression supports audience reinforcement; the
within-creator test is suggestive at the available sample size. (Side nulls:
algospeak-evasion and views-before/after-demonetisation both null once
controlled.)

---

## PART VII — #3 Podcast-vs-main register (case study)
*(results/17_podcast_vs_main_register.csv)*

Within-creator format delta for **h3** (24 main vs 20 podcast videos; lighter form,
not topic-matched):

| /100 words | Main | Podcast |
|---|---|---|
| profanity | 0.197 | 0.028 |
| explicit-sensitive | 0.223 | 0.165 |
| algospeak | 0.068 | 0.081 (ns) |

The **sponsor-heavy podcast is the cleaner register** — money-dependence tracks
cleaner language via *format*, consistent with the thesis. **Caveats:** n=1 creator
(second channels like MoistCr1TiKaL lack usable captions, so #3 can't scale);
auto-captions bleep profanity, so that metric partly measures caption-censorship.
Descriptive only.

---

## PART VIII — Measurement validity & defensibility *(#4, #6)*

### #4 — Detector precision vs recall
*(results/18_detector_precision_recall.csv)*

- The project's **strict** detector (bleeps + letter-masks + unambiguous coded
  terms) is high precision (hand-validated).
- The broad 35-term euphemism **lexicon** has **~50% precision**: of 375 videos it
  flags, **181 (48%) are flagged only via benign words** (`sa` 200, `corn` 92,
  `accountant` 18, `mascara`, `panini`…). Broadening to raise recall backfires.
- Genuine coded terms are **sparse** (~50 videos: grape 33, cheeto 6, pdf file 4,
  unalive 2…), so little lexical masking is being missed. True recall is deferred
  to the #2 human reference set rather than asserted.

### #6 — Three anticipated questions, pre-answered
| Anticipated question | Prepared answer |
|---|---|
| *Are the LLM judges reliable?* | #2 human validation (kappa + human-vs-A/B); the gap is measured *between* two instruments on the *same* videos, controlling shared error; #7 shows where System A is genuinely uncertain. |
| *Does masking actually prevent demonetisation?* | No — the **controlled counterfactual** shows algospeak *raises* the policy judge's demonetise rate (reads as evasion) and the **leaky mask** shows it coexists with the plain word at no ad cost. Masking is ritual, not a working filter-dodge. |
| *Are these creators actually demonetised?* | The corpus is a **general sensitive-genre sample, not a verified demonetised cohort.** Ad-serving evidence establishes *monetisation* only for videos where an ad was observed (one-directional rule). We report **predicted risk** (System A/B) and **verified monetisation** (ads) as separate, clearly-labelled quantities and never infer demonetisation from model output. |

## Corpus & methods (appendix)

- **Master transcript corpus:** 3,617 videos, 65 channels (union of euph corpus +
  dataset, dedup, ≥50 words). 2,106 with descriptions, 555 with live ad data.
- **Meta-discourse corpus (this session):** 62 rant · 29 official · 19 advice ·
  4 news · 4 interview.
- **System A:** official-policy RAG judge (qwen3:8b + nomic-embed-text, 61-chunk
  policy index) on a university 4×H100 server.
- **System B:** folk-theory judge, rules distilled from a Reddit/X folk corpus.
- **Masking detector:** deterministic (bleeps + masked spellings + validated coded
  terms), ~100% precision — the reliable behavioural signal.
- **Inference discipline:** one-directional ad rule (ad present ⇒ monetised; absent
  proves nothing); five label types kept separate; within-video/within-creator
  pairing; creator-clustered bootstrap; Wilson CIs; permutation tests. No synthetic
  labels; unknowns marked unknown.

## Honest limitations
- English-language; discovery via ytsearch is popularity-biased.
- The corpus is a **general sensitive-genre sample, not a verified demonetised
  cohort** — we never infer demonetisation from model predictions.
- LLM judges are instruments with their own error; the gap is measured *between*
  two such instruments on the same videos, which controls shared error.
- Many headline effects are **modest in absolute terms**; the contribution is the
  *structure* (belief ≫ reality; talk ≠ walk), not large behavioural magnitudes.

---

*Generated for the MSc thesis "Investigating YouTube Self-Censorship Practices."
The supporting data for every result above is committed as CSVs in
[`results/`](../results/) — see [`results/index.csv`](../results/index.csv) for
the section → CSV → producing-script map.*
