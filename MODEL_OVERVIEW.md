# Model Overview

This file explains the current baseline family in both **design** and **implementation** terms.

The goal is to answer four practical questions:

1. Why do we have these models?
2. How do the five core baselines differ conceptually?
3. What are we currently doing for query expansion and reranking?
4. How do we evaluate these systems on snapshot-1 train and on cumulative month growth?

The repo now evaluates systems at three levels:

- whole-train comparison on `snapshot-1 train`
- cumulative monthly split comparison inside `snapshot-1`
- temporal change comparison derived from the monthly results

## Current Model Inventory

Right now, the repository has **16 current models** that we treat as meaningful comparison systems:

- 5 base models
- 5 temporal sibling models
- 3 citation-aware temporal sibling models
- 3 fusion models

The clean mental model is:

- base models = the main non-temporal benchmark set
- temporal sibling models = the same base ideas, but with the temporal overlay enabled
- fusion models = run-level RRF combinations built from existing first-stage outputs

These 16 models are the current evaluation inventory for:

- whole-train effectiveness
- monthly split robustness
- temporal change analysis

## Why We Have This Baseline Family

We want one coherent baseline suite that answers three different questions:

1. What do the **official organizer baselines** look like?
2. How strong can a **non-temporal lexical baseline** become?
3. Do **dense retrieval, fusion, and reranking** really help on this benchmark?

That gives us two official anchors and three custom overlays built on top of them.

## The Five Base Models

## 1. `official_pyterrier`

Design idea:

- official lexical anchor
- BM25 scoring
- title + abstract document representation

Why it matters:

- this is the canonical sparse baseline
- it is our natural pivot for later change-in-effectiveness analysis
- if a custom method cannot beat this, it is not yet a strong Run 1 system

Implementation note:

- in the codebase, this is the PyTerrier BM25 path
- the "model" here is Terrier BM25, not a neural checkpoint

## 2. `official_pyterrier_dense`

Design idea:

- official dense anchor
- embedding-based retrieval
- Qwen embedding model

Why it matters:

- this is the official dense comparison point
- it tells us how far a modern semantic baseline can go
- it is the baseline we want to improve on with stronger custom dense or hybrid systems

Implementation note:

- this follows the upstream dense baseline shape
- it depends on the local embedding service expected by the official script

## 3. `custom_lexical_fulltext`

Design idea:

- lexical retrieval
- full-text document view
- stronger sparse challenger to the official BM25 setup

Why it matters:

- the 2025 overview suggests full-text BM25 is extremely competitive in scientific retrieval
- it gives us the strongest simple sparse baseline before adding more complicated methods
- it is currently the strongest train-split method in our local results

## 4. `custom_title_abstract_rm3`

Design idea:

- title + abstract BM25
- RM3 pseudo-relevance feedback
- expanded query over the shared title + abstract lexical index

Why it matters:

- this is the clean query-expansion overlay on top of the official lexical representation
- it isolates whether reformulation helps without changing the first-stage index
- it is the simplest sparse baseline improvement suggested by the LongEval and OpenWebSearch evidence

## 5. `custom_title_abstract_rerank`

Design idea:

- title + abstract BM25 candidate generation
- cross-encoder reranking over the head of the lexical candidate list
- untouched lexical tail appended for full-depth evaluation

Why it matters:

- this tests whether reranking alone improves the official lexical representation
- it is a direct non-temporal overlay on top of the official BM25-style first stage
- it is our simplest second-stage ranking experiment before temporal features

## The Five Temporal Sibling Models

These are paired variants of the five base models. They keep the same first-stage retrieval idea, but add the temporal rerank overlay.

## 6. `official_pyterrier_temporal`

Design idea:

- BM25 title + abstract baseline
- temporal metadata and intent-aware rerank overlay

Why it matters:

- lets us compare plain official BM25 against a time-aware refinement of the same system

## 7. `official_pyterrier_dense_temporal`

Design idea:

- official dense Qwen baseline
- temporal rerank overlay on top of the existing dense run

Why it matters:

- isolates whether temporal refinement helps the official dense anchor without changing the dense index

## 8. `custom_lexical_fulltext_temporal`

Design idea:

- full-text BM25
- temporal rerank overlay

Why it matters:

- tests whether the strongest current sparse baseline also benefits from temporal cues

## 9. `custom_title_abstract_rm3_temporal`

Design idea:

- title + abstract BM25 with RM3 expansion
- temporal rerank overlay

Why it matters:

- combines query expansion with temporal reranking on the same lexical branch

## 10. `custom_title_abstract_rerank_temporal`

Design idea:

- title + abstract BM25
- cross-encoder reranking
- temporal rerank overlay on top of that existing rerank pipeline

Why it matters:

- this is currently the most layered lexical design in the repo
- it tests whether temporal refinement can improve an already reranked baseline

## The Three Fusion Models

These are non-temporal run-level fusion models. They do not build new indices. They reuse existing train-time run files and combine them with RRF.

## 11. `rrf_bm25_ta_dense_ta`

Design idea:

- RRF over BM25 title + abstract and dense title + abstract

Why it matters:

- the smallest lexical+dense fusion ablation

## 12. `rrf_bm25_ft_dense_ta`

Design idea:

- RRF over BM25 fulltext and dense title + abstract

Why it matters:

- the strongest current simple fusion baseline
- preserves the strong sparse full-text branch while adding semantic candidates

## 13. `rrf_bm25_ta_bm25_ft_dense_ta`

Design idea:

- RRF over BM25 title + abstract, BM25 fulltext, and dense title + abstract

Why it matters:

- the widest current first-stage fusion
- useful for recall-heavy analysis and for future `RRF -> rerank` experiments

## The Three Citation-Aware Temporal Models

These are focused Run 2 follow-ups for the three models we wanted to test first with OpenCitations features.

## 14. `official_pyterrier_temporal_citation`

Design idea:

- title + abstract BM25
- temporal rerank overlay
- citation-aware temporal features added on top

Why it matters:

- isolates whether citation-based scientific impact helps the official BM25 temporal sibling

Current local picture:

- modest improvement over `official_pyterrier_temporal`
- still much weaker than the non-temporal BM25 baseline

## 15. `custom_lexical_fulltext_temporal_citation`

Design idea:

- full-text BM25
- temporal rerank overlay
- citation-aware temporal features added on top

Why it matters:

- tests whether citation features can stabilize or improve the strongest sparse base model once temporal reranking is enabled

Current local picture:

- essentially unchanged from `custom_lexical_fulltext_temporal`
- the main issue is still the temporal weighting itself, not the absence of citation data

## 16. `custom_title_abstract_rerank_temporal_citation`

Design idea:

- title + abstract BM25
- cross-encoder reranking
- temporal rerank overlay
- citation-aware temporal features added on top

Why it matters:

- this is the most promising citation-aware Run 2 branch so far
- it combines lexical relevance, second-stage semantic reranking, and scientific impact signals

Current local picture:

- clearly stronger than the harsher temporal-only fulltext and BM25 temporal siblings
- still weaker than the best non-citation temporal rerank variant, so citation features are helping but not yet enough to dominate the leaderboard

## What Changed From Earlier Variants

Earlier in the project we also explored:

- `custom_dense_rerank`
- `custom_hybrid_union_rerank`
- `custom_hybrid_rrf_rerank`

Those were useful exploratory branches, but the current **canonical five-model comparison** is intentionally narrower:

- official lexical anchor
- official dense anchor
- fulltext lexical overlay
- title+abstract RM3 overlay
- title+abstract rerank overlay

This keeps Run 1 tightly focused on overlays over existing first-stage indices instead of proliferating additional dense and hybrid branches at the same time.

For Run 2, the temporal versions should be treated as **paired sibling systems** rather than silent replacements:

- `official_pyterrier` vs `official_pyterrier_temporal`
- `official_pyterrier_dense` vs `official_pyterrier_dense_temporal`
- `custom_lexical_fulltext` vs `custom_lexical_fulltext_temporal`
- `custom_title_abstract_rm3` vs `custom_title_abstract_rm3_temporal`
- `custom_title_abstract_rerank` vs `custom_title_abstract_rerank_temporal`

That gives us a clean way to ask:

- does temporal refinement help this base model?
- how much does it help?
- does it help raw effectiveness, temporal robustness, or both?

For fusion, the same pairing logic does not apply. The fusion models are separate systems built from existing run outputs rather than direct one-to-one siblings of a single base model.

## Fusion Is Not Its Own Model

One point that can be confusing is that **fusion methods are not retrieval models by themselves**.

For example:

- BM25 is a retrieval model
- Qwen dense retrieval is a retrieval model
- E5 dense retrieval is a retrieval model
- RRF is **not** a retrieval model

RRF, or **Reciprocal Rank Fusion**, is a rule for combining ranked lists that already came from other systems.

So RRF does not create candidates from scratch. Instead, it takes inputs like:

- a lexical ranking
- a dense ranking

and combines them into a new fused ranking.

That means RRF sits **between retrieval and reranking**:

1. run lexical retrieval
2. run dense retrieval
3. fuse the two candidate lists with RRF
4. rerank the fused pool

So when it looks like `custom_hybrid_rrf_rerank` “cannot use those models,” the real issue is not that RRF is special in a bad way. The real point is:

- RRF itself does not have a model checkpoint
- it can only use whatever upstream candidate generators we plug into it

In our current implementation, those upstream generators are:

- lexical full-text retrieval
- dense title + abstract retrieval

If we later want `RRF + rerank` to use different upstream systems, we would swap the candidate generators, not the RRF logic itself.

Examples:

- BM25 + Qwen dense -> RRF -> rerank
- BM25 + E5 dense -> RRF -> rerank
- BM25 full text + BM25 title/abstract -> RRF -> rerank

So RRF is best understood as a **fusion layer**, not a standalone retriever.

Important implementation rule:

- RRF should fuse **existing run outputs**
- RRF should **not** trigger any new index build
- RRF should reuse the same snapshot-level retrieval artifacts we already produced

So when we add fusion back into the main workflow, it should look like:

1. run first-stage retrieval systems
2. read their run files
3. fuse them with RRF
4. optionally rerank the fused head

That keeps fusion cheap and makes it compatible with the official BM25 and official dense anchors.

Current first RRF ablations on `snapshot-1 train` show:

- `RRF(BM25 title+abstract, Dense title+abstract)` is weaker than the best individual sparse baseline
- `RRF(BM25 fulltext, Dense title+abstract)` is the strongest of the first RRF variants
- `RRF(BM25 title+abstract, BM25 fulltext, Dense title+abstract)` improves recall strongly, but still does not beat pure fulltext BM25 on nDCG@10

So the early lesson is:

- run-level fusion is cheap and useful to test
- but simple RRF is not automatically better than the strongest sparse baseline
- the best next step is likely `RRF -> rerank`, not RRF alone

## Current Query Expansion

### Short Answer

Until now, the five baseline family has had **no real query expansion**.

That means there has been:

- no RM3
- no pseudo-relevance feedback
- no keyquery expansion
- no history-aware qrel boosting
- no LLM rewriting

Each baseline has been using the original query text from the dataset.

That is one of the biggest remaining gaps in Run 1.

## Current Query Expansion Overlay

We now have one explicit query-expansion overlay in the canonical five-model set:

- `custom_title_abstract_rm3`

Design idea:

- start from the shared title + abstract lexical baseline
- apply RM3 pseudo-relevance feedback
- rerun lexical retrieval with the expanded query

Why it matters:

- it is the cleanest title+abstract lexical expansion baseline
- it directly tests one of the strongest non-temporal ideas suggested by the 2025 evidence
- it improves the official lexical branch without introducing temporal signals

Important positioning:

- this is one of the current five canonical comparison systems
- it is meant to sit on top of the shared title+abstract lexical index

## Current Reranking

Reranking is currently used in the canonical five-model set only in:

- `custom_title_abstract_rerank`

It is not used in:

- `official_pyterrier`
- `official_pyterrier_dense`
- `custom_lexical_fulltext`
- `custom_title_abstract_rm3`

### How `custom_title_abstract_rerank` Uses Reranking

1. retrieve lexical candidates
2. use title + abstract text for the rerank stage
3. rerank the head of the lexical candidate list with a cross-encoder-style scorer
4. append the remaining lexical tail unchanged
5. output the final ranked list

### Important Practical Detail

The reranker class is [`CrossEncoderReranker`](c:/Users/Will/Documents/longEval2026task1/src/longeval_sci/rerank/cross_encoder.py).

If the model-backed path loads correctly, we use the configured cross-encoder.
If it does not, the code falls back to a simple lexical overlap scorer.

So reranking is present structurally, but its quality still depends on the runtime environment and model availability.

## Fielding Strategy Across the Models

One of the main lessons from the 2025 evidence is already reflected in our design:

- lexical retrieval tends to benefit from **full text**
- dense retrieval tends to behave better on **title + abstract**

Current field split:

- `official_pyterrier`
  - lexical BM25 over `title_abstract`
- `official_pyterrier_dense`
  - dense retrieval over `title_abstract`
- `custom_lexical_fulltext`
  - lexical retrieval over `full_text`
- `custom_title_abstract_rm3`
  - lexical retrieval over `title_abstract` with RM3 expansion
- `custom_title_abstract_rerank`
  - lexical candidates from `title_abstract`
  - reranking also uses `title_abstract`

This is already a strong non-temporal design principle for LongEval-Sci.

## How to Read the Current Baseline Family

The five core models form a progression:

1. official sparse anchor
2. official dense anchor
3. stronger sparse custom baseline
4. title+abstract query-expansion overlay
5. title+abstract rerank overlay

The RM3 run should be read as an extension of the title+abstract sparse branch:

- official sparse anchor
- stronger full-text sparse baseline
- title+abstract sparse baseline with query expansion

So we are now comparing design choices like:

- sparse vs dense
- title+abstract vs full-text lexical retrieval
- retrieval-only vs reranked pipelines
- original query vs expanded query

## Recommended Next Phase 1 Additions

The next improvements should remain **non-temporal** and should build on the current family.

Recommended order:

1. `BM25 full text`
2. `BM25 title_abstract + RM3`
3. `BM25 title_abstract + rerank`
4. later, add denser semantic and hybrid branches back as targeted ablations if needed

That means the next design levers to prioritize are:

- stronger lexical expansion
- better candidate pool quality
- reranker ablations
- better fusion than plain union

The repo now includes a direct hook for that next step:

- rerank sweep support
  - scripted comparison of rerank depth and reranker model choices on `snapshot-1 train`

## Current Local Picture

On `snapshot-1` train with the provided qrels:

- among the five base models, `custom_lexical_fulltext` is strongest
- among the three current fusion models, `rrf_bm25_ft_dense_ta` is strongest
- among the temporal sibling models, `official_pyterrier_dense_temporal` is currently strongest
- among the citation-aware temporal models, `custom_title_abstract_rerank_temporal_citation` is currently strongest
- several temporal siblings are currently much weaker than their base models, which tells us the first temporal weighting pass is still very rough

So the main near-term research move is not to add temporal modeling yet, but to improve:

- lexical expansion
- reranking effectiveness
- temporal weighting stability
- citation-feature weighting
- and then study how all 16 systems behave under cumulative month growth using the monthly reports
