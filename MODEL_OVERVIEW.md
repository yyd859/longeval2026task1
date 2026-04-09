# Model Overview

This file explains the **five current baselines** in design terms, without going deep into implementation details.

## Why We Have Five Models

We want one small family of baselines that answers three different questions:

1. What do the **official organizer baselines** look like?
2. How far can we push a **strong lexical baseline** without explicit temporal modeling?
3. Do **dense retrieval** or **reranking** actually help on this benchmark?

That gives us two official anchors and three custom research baselines.

## 1. `official_pyterrier`

Design idea:

- classic lexical retrieval
- BM25 scoring
- title + abstract style document representation

Why it matters:

- this is the canonical official sparse baseline
- it gives us a trustworthy reference point
- if our custom systems cannot beat this, they are not yet strong enough

## 2. `official_pyterrier_dense`

Design idea:

- dense retrieval baseline from the official LongEval scientific-retrieval repo
- Qwen embedding model
- embedding-based nearest-neighbor search instead of term matching

Why it matters:

- this is the official dense anchor
- it tells us how far a modern embedding-only baseline can go
- it is the main official comparison point for later dense or hybrid methods

## 3. `custom_lexical_fulltext`

Design idea:

- still lexical
- but uses the **full text cache** rather than only title + abstract
- tries to capture a stronger sparse baseline through richer document text

Why it matters:

- it tests whether full text gives a meaningful gain over the official BM25 setup
- it is still easy to interpret
- it is currently the strongest train-split model in our local results

## 4. `custom_dense_rerank`

Design idea:

- dense retrieval creates an initial candidate set
- a reranker then rescoring those candidates tries to improve ordering

Why it matters:

- this is our first “stronger than plain retrieval” custom pipeline
- it tests the value of reranking separately from hybrid fusion
- if this works well later, it becomes a natural base for Run 2 extensions

## 5. `custom_hybrid_union_rerank`

Design idea:

- combine lexical and dense candidates
- take the union of both candidate sets
- rerank the merged pool

Why it matters:

- this tests whether lexical and dense are complementary
- it is the most natural “strong baseline stack” before time-aware methods
- it is also the most extensible design for future Run 2 and Run 3 additions

## Practical Interpretation

The five models are not just five arbitrary runs.

They form a progression:

1. official sparse anchor
2. official dense anchor
3. stronger sparse custom baseline
4. dense + rerank custom baseline
5. hybrid + rerank custom baseline

So when we compare them, we are really comparing design choices:

- sparse vs dense
- abstract-only vs fulltext
- retrieval-only vs reranked
- single-source candidates vs hybrid candidates

## Current Local Picture

On `snapshot-1` train with the provided qrels:

- `custom_lexical_fulltext` is currently strongest
- `official_pyterrier` matches the downloaded official BM25 reference
- the custom dense and hybrid pipelines still need tuning

That means our next likely research move is not “add more models blindly,” but:

- improve dense retrieval quality
- inspect reranker behavior
- understand why lexical fulltext is currently so dominant
