# Temporal Features Design

This document defines the **Run 2** design for adding temporal features to the current five-model LongEval-Sci workflow.

The goal is to move from:

- strong non-temporal baselines and overlays

to:

- time-aware retrieval and reranking that still fit the benchmark structure cleanly

without breaking the current Run 1 pipeline.

## Current Base Models

Run 2 should build on the existing five-model comparison set:

1. `official_pyterrier`
2. `official_pyterrier_dense`
3. `custom_lexical_fulltext`
4. `custom_title_abstract_rm3`
5. `custom_title_abstract_rerank`

These remain the **base models**.

Run 2 does not replace them. It adds temporal-aware variants and temporal-aware analysis on top of them.

## Fusion as an Overlay, Not an Index Type

Before implementing heavier temporal modules, we should preserve one important design rule from the current baseline structure:

- fusion belongs **after retrieval**
- fusion should operate on **existing run outputs**
- fusion should **not** create a new index type
- fusion should **not** trigger any index rebuild

This matters because our first-stage retrieval artifacts are already expensive:

- title + abstract lexical index
- fulltext lexical index
- official dense title + abstract index

If we want to combine:

- BM25 over title + abstract
- BM25 over fulltext
- dense retrieval over title + abstract
- later, RM3-expanded lexical retrieval

the right place to do that is at the **run level**, not the indexing layer.

Recommended first fusion method:

- `RRF` (Reciprocal Rank Fusion)

Recommended interpretation:

```text
indexing stage: unchanged
retrieval stage: unchanged
fusion stage: new
reranking stage: optional, after fusion
```

That means the first implementation should read existing per-snapshot run files, fuse them, and write a new fused run without rebuilding any first-stage index.

Suggested code layout:

```text
src/longeval_sci/fusion/
  __init__.py
  rrf.py

scripts/
  run_rrf_fusion.py
```

Suggested interface:

```python
rrf_fuse(
    runs: list[pd.DataFrame],
    k: int = 60,
    top_k: int = 1000,
    run_name: str = "rrf",
) -> pd.DataFrame
```

Suggested first experiments:

1. `RRF(BM25 title_abstract, Dense title_abstract)`
2. `RRF(BM25 fulltext, Dense title_abstract)`
3. `RRF(BM25 title_abstract, BM25 fulltext, Dense title_abstract)`

Important boundary:

- do not put fusion inside index construction
- do not modify document encoding just to support fusion
- do not rebuild the dense index just to add RRF

Fusion should be treated as a cheap overlay on top of existing snapshot-level run artifacts.

## Run 2 Objective

Run 1 optimizes:

- raw effectiveness

Run 2 should optimize:

- effectiveness under collection evolution
- robustness when newer documents are added
- behavior differences between stable and changing information needs

In code terms, Run 2 should introduce **temporal modules** that can be attached to:

- retrieval
- reranking
- query expansion
- historical reuse

while preserving the current baseline paths.

## Temporal Signal Buckets

There are two broad temporal signal families.

## 1. Metadata-Side Temporal Signals

These come from document and snapshot metadata.

Candidate features:

- publication / creation date
- last update / modification date
- snapshot membership
- document age relative to evaluation point
- time since last update
- citation count as of the evaluation cutoff
- recent citation count as of the evaluation cutoff
- non-self citation count
- citation velocity / trend
- age bucket:
  - very recent
  - recent
  - medium
  - old
- recency decay value
- freshness gain value

Why they matter:

- they are easy to compute
- they align with the benchmark structure
- they can be used before adding heavier content-side temporal modeling
- they can be extended cleanly with the local OpenCitations file without rebuilding first-stage retrieval

## 2. Content-Side Temporal Signals

These come from the query or document text.

Candidate features:

- whether the query implies recency or currentness
- whether the query is foundational / background
- whether the query is about an evolving topic
- whether the document terminology looks novel relative to earlier data
- lexical novelty against prior months or prior snapshots
- whether the document appears survey-like or state-of-the-art focused

Why they matter:

- metadata alone will miss many temporal information needs
- some queries require older foundational papers
- some queries need recent or updated material

Run 2 should combine both metadata-side and content-side temporal cues.

## Four Run 2 Modules

The design should be organized around four modules.

In addition, Run 2 should reserve a lightweight overlay path for:

- run-level fusion

This is not a fifth temporal module in the same sense as intent, reranking, history, and clustering. It is a cross-cutting orchestration layer that can be applied before or after some temporal components.

## A. Temporal Intent Classifier

Purpose:

- classify the query into a temporal need category

Suggested classes:

- `foundational`
- `current`
- `evolving`
- `survey`

Interpretation:

- `foundational`
  - older canonical papers may be preferred
- `current`
  - recent or newly updated documents may be preferred
- `evolving`
  - both strong history and recent developments may matter
- `survey`
  - broad overview papers, often not necessarily the newest

Recommended first implementation:

- a lightweight rule-based baseline using:
  - query lexical cues
  - query length
  - temporal keywords
- then later:
  - a learned classifier

Suggested code location:

- `src/longeval_sci/temporal/intent.py`

Suggested output object:

```python
TemporalIntentPrediction(
    label: str,
    scores: dict[str, float],
)
```

How it plugs in:

- queried before temporal reranking
- used as a routing signal for feature weighting

## B. Time-Aware Reranking

Purpose:

- use temporal features to reorder candidates after first-stage retrieval

This should become the main Run 2 mechanism.

Suggested feature groups:

- base retrieval score
- base reranker score
- document age
- time since last update
- recency bucket
- temporal intent class
- query-document age compatibility
- lexical novelty score
- snapshot-relative freshness

Recommended first implementation:

- feature-based reranker over the current candidate set
- keep the current retrieval pipeline unchanged
- add a temporal rescoring layer after retrieval and before final output

Simple first scoring formula:

```text
temporal_score =
  w_base * base_score
  + w_rerank * rerank_score
  + w_age * age_feature
  + w_update * update_feature
  + w_novelty * novelty_feature
```

where the weights depend on the query temporal intent.

Suggested code location:

- `src/longeval_sci/temporal/rerank.py`

Suggested interface:

```python
rerank_with_temporal_features(
    query,
    candidates,
    temporal_intent,
    evaluation_time,
    config,
) -> list[tuple[str, float]]
```

How it plugs in:

- after the current candidate generation
- can sit on top of:
  - `official_pyterrier`
  - `official_pyterrier_dense`
  - `custom_lexical_fulltext`
  - `custom_title_abstract_rm3`
  - `custom_title_abstract_rerank`

## C. Historical Transfer

Purpose:

- reuse useful prior information when a query or near-duplicate query has historical evidence

This is where prior relevance or prior successful documents can help.

Candidate behaviors:

- query exact-match history lookup
- near-duplicate query matching
- prior relevant document boosting
- prior expansion term reuse
- prior top-document reuse as a candidate bonus

Recommended first implementation:

- exact and near-duplicate query matching only
- no deep clustering yet

Suggested data sources:

- earlier query text
- earlier qrels
- earlier run outputs

Suggested code location:

- `src/longeval_sci/temporal/history.py`

Suggested output:

```python
HistoricalHints(
    prior_docs: list[str],
    prior_terms: list[str],
    similarity: float,
)
```

How it plugs in:

- optional score boost before final reranking
- optional candidate augmentation
- optional RM3 term prior

## D. Cluster Fallback

Purpose:

- borrow historical signals when exact query matches do not exist

This is a softer version of historical transfer.

Candidate workflow:

1. encode the current query
2. find similar historical queries
3. cluster them or retrieve nearest neighbors
4. borrow priors from the cluster

Possible borrowed signals:

- likely temporal intent
- likely useful prior documents
- likely expansion terms
- likely recency preference

Recommended first implementation:

- nearest-neighbor query fallback, not full unsupervised clustering

Suggested code location:

- `src/longeval_sci/temporal/cluster.py`

How it plugs in:

- only if exact history is missing
- provides hints to the temporal reranker

## Coding Architecture

Run 2 should add a new package:

```text
src/longeval_sci/temporal/
  __init__.py
  intent.py
  features.py
  rerank.py
  history.py
  cluster.py
  scoring.py

src/longeval_sci/fusion/
  __init__.py
  rrf.py
```

Recommended responsibilities:

- `intent.py`
  - classify query temporal intent
- `features.py`
  - compute temporal metadata and content features
- `rerank.py`
  - apply temporal reranking
- `history.py`
  - exact/near-duplicate historical transfer
- `cluster.py`
  - fallback transfer from similar queries
- `scoring.py`
  - shared scoring functions and weight logic
- `fusion/rrf.py`
  - run-level reciprocal rank fusion over existing retrieval outputs

## Integration With Current Pipelines

Run 2 should be added as **optional overlays**, not as hard forks.

### For `official_pyterrier`

Add:

- temporal rerank after BM25 candidates

### For `official_pyterrier_dense`

Add:

- temporal rerank after official dense candidates

### For `custom_lexical_fulltext`

Add:

- temporal rerank after fulltext BM25
- later, temporal query expansion weighting if useful

### For `custom_title_abstract_rm3`

Add:

- temporal rerank after RM3-expanded lexical retrieval

### For `custom_title_abstract_rerank`

Add:

- temporal feature augmentation on top of the current rerank stage

### For Run-Level Fusion

Add:

- RRF over existing snapshot-level runs
- optional temporal rerank on top of the fused run

This should support combinations like:

- `official_pyterrier + official_pyterrier_dense`
- `custom_lexical_fulltext + official_pyterrier_dense`
- `official_pyterrier + custom_lexical_fulltext + official_pyterrier_dense`
- later, `custom_title_abstract_rm3` as an additional fusion input

That means Run 2 should mostly look like:

```text
first-stage retrieval
-> optional RM3 / existing rerank
-> optional run-level fusion
-> temporal intent
-> temporal feature scoring
-> final rerank
```

When fusion is used, the preferred order is:

```text
first-stage retrieval
-> optional RM3
-> optional existing rerank
-> run-level fusion
-> optional temporal rerank
-> final output
```

## Config Design

Run 2 should add a new config block, not overload existing retrieval fields.

Suggested config shape:

```yaml
temporal:
  enabled: true
  evaluation_time_field: snapshot
  metadata_features:
    use_creation_date: true
    use_update_date: false
    use_age: true
    use_recency_decay: true
  content_features:
    use_query_intent: true
    use_lexical_novelty: true
  history:
    enabled: true
    exact_match_only: false
    top_k_prior_docs: 20
  cluster_fallback:
    enabled: false
    top_k_similar_queries: 10
```

This should live beside the existing:

- `retrieval`
- `expansion`
- `rerank`

blocks.

## Data Dependencies

Run 2 requires better access to temporal metadata.

The loader should expose, for each document where available:

- creation date
- update date
- snapshot id

and for each snapshot:

- snapshot timestamp
- prior snapshot references if available

Suggested normalization rule:

- store all temporal fields in `Document.metadata`
- add helper functions that convert metadata into comparable datetimes

Citation-specific note:

- the local OpenCitations file should be treated as a second temporal metadata source
- citation edges must be filtered by `creation <= evaluation_cutoff`
- citation features should be precomputed per cutoff and then reused by temporal rerankers
- see [TEMPORAL_CITATION_FEATURES.md](c:/Users/Will/Documents/longEval2026task1/TEMPORAL_CITATION_FEATURES.md)

Current repo choice:

- `createdDate` is the primary temporal field for the current Run 2 overlays
- `updatedDate` is disabled by default in the temporal configs because many update timestamps fall outside the intended development window

## Evaluation Design

Run 2 evaluation should use two layers.

### 1. Absolute effectiveness

Still track:

- `nDCG@10`
- `MAP`
- `Recall`

### 2. Temporal robustness

Use:

- cumulative monthly split reports
- temporal change report
- RI / DRI / ER / ARP / MARP

Pivot system:

- `official_pyterrier`

This is important because Run 2 should not just improve raw scores; it should improve robustness under change.

In practice, the current evaluation flow is:

1. whole-train evaluation on `snapshot-1 train`
   - main report: `outputs/reports/all_models_train_snapshot1/summary.md`
2. cumulative monthly split evaluation
   - main report: `outputs/reports/monthly_split/_summary/monthly_comparison.md`
3. temporal change evaluation
   - main report: `outputs/reports/monthly_split/_summary/temporal_change/temporal_change.md`

So Run 2 analysis should always be read across all three layers:

- full-train effectiveness
- month-growth robustness
- pivot-relative temporal change

## Monitoring and User Feedback

Temporal and fusion overlays should be easy to monitor while they run.

When we implement them, they should provide:

- startup logs that list:
  - input run paths
  - output path
  - number of queries
  - whether existing runs are being reused
- periodic progress logs while processing queries
- a lightweight progress file in the output directory, similar to the current rerank progress tracking

Important usability rule:

- users should be able to tell whether the process is:
  - loading runs
  - fusing runs
  - computing temporal features
  - reranking
  - writing outputs

This is especially important because Run 2 should feel like a controlled overlay on top of existing artifacts, not like another opaque reindexing process.

## Recommended Build Order

The best implementation order is:

1. temporal metadata feature extraction
2. query temporal intent baseline
3. temporal rerank overlay
4. exact historical transfer
5. near-duplicate history
6. cluster fallback

That order keeps the repo stable and gives useful incremental results early.

## What Not To Do Yet

Run 2 should still stay disciplined.

Do not do yet:

- end-to-end retraining of new dense models
- full adaptive refresh policy
- large unsupervised clustering pipeline first
- trigger-policy logic for update scheduling

Those belong to later work, especially Run 3.

## Deliverables for the First Technical Pass

The first technical Run 2 pass should aim to produce:

1. a temporal config block
2. document-time feature extraction utilities
3. a rule-based temporal intent classifier
4. a temporal reranking overlay for at least:
   - `official_pyterrier`
   - `custom_lexical_fulltext`
   - `custom_title_abstract_rerank`
5. a run-level RRF fusion utility that reuses existing snapshot-level runs
6. evaluation on:
   - `snapshot-1 train`
   - cumulative monthly growth splits
   - temporal change report

That would give us a clean, explainable Run 2 foundation before we dive into the technical details of scoring, feature weighting, and historical transfer.
