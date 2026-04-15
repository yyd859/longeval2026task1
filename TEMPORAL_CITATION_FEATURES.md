# Temporal Citation Features

This note explains how to use the local OpenCitations file:

- `\.cache\ir_datasets\longeval-sci-2026\longeval-sci-2026-citation-network.csv`

for **as-of-snapshot-date citation features** in our current LongEval-Sci models.

## Why Citation Features Belong in Run 2

Our current temporal features are built mainly from:

- `createdDate`
- `publishedDate`
- `updatedDate`
- query intent
- lexical novelty

That is useful, but incomplete. Citation behavior gives us a second, different kind of temporal evidence:

- which documents have become influential
- which documents are currently gaining attention
- which documents look foundational rather than just recent
- how quickly a document begins attracting citations

This fits the Run 2 goal well because it captures **temporal scientific impact**, not just document age.

## What Is In the OpenCitations File

Current columns:

- `id`
- `citing`
- `cited`
- `creation`
- `timespan`
- `journal_sc`
- `author_sc`
- `citing_doc_id`
- `cited_doc_id`

Important practical observations:

- `creation` is the citation-edge time signal we should treat as the timestamp for "this citation existed by then"
- `cited_doc_id` and `citing_doc_id` connect many citation edges directly to our local corpus doc ids
- `journal_sc` and `author_sc` let us separate self-citation from broader impact
- `timespan` gives a citation-lag signal

## Leakage Rule

This is the most important rule:

- only use citation edges whose `creation` date is **on or before the evaluation cutoff**

That means:

- for `snapshot-1 train` we should cap citations at the snapshot-1 cutoff
- for `march_only` use the March cutoff
- for `march_april` use the April cutoff
- for `march_april_may` use the May cutoff

We should never let a March evaluation use citations that were created in April or May.

## Recommended First Citation Features

We should start with a small, explainable set.

### 1. Inbound impact features

Per document, as of the cutoff:

- total inbound citations
- non-self inbound citations
- recent inbound citations
- non-self recent inbound citations

Why:

- strong signal for scientific impact
- useful for distinguishing foundational papers from weakly connected documents

### 2. Citation trend features

Per document, as of the cutoff:

- recent inbound ratio = `recent_inbound / total_inbound`
- citation velocity = `recent_inbound / recent_window_days`
- emerging signal

Why:

- helps detect documents that are currently rising in attention
- especially useful for `current` and `evolving` queries

### 3. Foundationality features

Per document, as of the cutoff:

- foundational citation signal
- mean inbound citation lag

Why:

- helps identify older, well-established work
- useful for `foundational` and `survey` queries

### 4. Outbound reference behavior

Per document, as of the cutoff:

- total outbound citations
- recent outbound citations

Why:

- useful later for identifying survey-like or reference-heavy documents
- less important than inbound features for the first pass

## How To Use These Features With the Current Models

Citation features should be used as **rerank overlays**, not as new first-stage retrievers.

That means:

- no new lexical index
- no new dense index
- no rebuilding first-stage retrieval just because we added citations

### Base models

Use citation features in the temporal sibling rerankers for:

- `official_pyterrier`
- `official_pyterrier_dense`
- `custom_lexical_fulltext`
- `custom_title_abstract_rm3`
- `custom_title_abstract_rerank`

Recommended interpretation:

- `official_pyterrier_temporal`
  - BM25 title+abstract + citation-aware temporal rerank
- `official_pyterrier_dense_temporal`
  - dense title+abstract + citation-aware temporal rerank
- `custom_lexical_fulltext_temporal`
  - BM25 fulltext + citation-aware temporal rerank
- `custom_title_abstract_rm3_temporal`
  - BM25 title+abstract + RM3 + citation-aware temporal rerank
- `custom_title_abstract_rerank_temporal`
  - BM25 title+abstract + cross-encoder + citation-aware temporal rerank

### Fusion models

For the RRF models, citation features should be added **after fusion**:

- retrieval
- optional rerank
- RRF
- citation-aware temporal rerank

So citation features remain a run-level overlay here too.

## Query-Intent Routing

Citation features should not have one fixed effect for every query.

Recommended weighting logic:

### `foundational`

Boost:

- total inbound citations
- non-self inbound citations
- foundational citation signal

Use cautiously:

- recent citation trend

### `current`

Boost:

- recent inbound citations
- citation velocity
- emerging signal

Use cautiously:

- total legacy citation count

### `evolving`

Blend:

- foundational signal
- emerging signal
- recent inbound ratio

### `survey`

Boost:

- total inbound citations
- outbound citation richness
- foundational signal

## Recommended Cutoffs

For our current internal evaluation:

- `snapshot-1 train`
  - snapshot-1 cutoff
- `march_only`
  - end of March 2025
- `march_april`
  - end of April 2025
- `march_april_may`
  - end of May 2025

That matches the current cumulative month-growth evaluation design.

Current snapshot cutoff mapping in code:

- `snapshot-1` -> `2025-05-31 23:59:59 UTC`
- `snapshot-2` -> `2025-08-31 23:59:59 UTC`
- `snapshot-3` -> `2025-11-30 23:59:59 UTC`

## Practical Implementation Plan

The right process is:

1. load the citation CSV once
2. stream rows and keep only edges with `creation <= cutoff`
3. aggregate per-document citation stats
4. cache those stats per cutoff
5. let temporal rerankers read the cached features instead of rereading the raw 27M-row CSV for every query

This is important because the citation file is large enough that repeated full scans would become annoying quickly.

## Current Utility Module

We now have a first helper module:

- [citations.py](c:/Users/Will/Documents/longEval2026task1/src/longeval_sci/temporal/citations.py)

It currently provides:

- `aggregate_citation_features(...)`
- `CitationTemporalFeatures`

This first pass is intentionally simple:

- stream the raw CSV
- enforce the as-of-cutoff rule
- compute raw and lightly normalized citation signals

It is not yet wired into the temporal reranker automatically.

## Recommended Next Coding Step

The next clean integration step is:

1. extend the temporal config with citation controls
2. build a cached citation feature store per cutoff
3. merge citation features into `TemporalDocumentFeatures`
4. add citation-aware weighting in the temporal reranker
5. compare:
   - no temporal features
   - temporal metadata only
   - temporal metadata + citation features

That comparison will tell us whether citation data improves:

- raw `snapshot-1 train` effectiveness
- monthly growth robustness
- temporal change metrics relative to the BM25 pivot

## Replication Commands

Current tested citation-aware models:

- `official_pyterrier_temporal_citation`
- `custom_lexical_fulltext_temporal_citation`
- `custom_title_abstract_rerank_temporal_citation`

Build the citation-aware temporal runs from existing train runs:

```powershell
python scripts/run_temporal_overlay.py --config configs/official_pyterrier_temporal_citation.yaml --input-run outputs/official_pyterrier/snapshot-1-train/run.txt --train-snapshot1 --qrels-variant dctr
python scripts/run_temporal_overlay.py --config configs/custom_lexical_fulltext_temporal_citation.yaml --input-run outputs/custom_lexical_fulltext/snapshot-1-train/run.txt --train-snapshot1 --qrels-variant dctr
python scripts/run_temporal_overlay.py --config configs/custom_title_abstract_rerank_temporal_citation.yaml --input-run outputs/custom_title_abstract_rerank/snapshot-1-train/run.txt --train-snapshot1 --qrels-variant dctr
```

Run the month-growth evaluation for those models:

```powershell
python scripts/run_snapshot1_monthly_eval.py --config configs/official_pyterrier_temporal_citation.yaml --plan configs/plans/snapshot1_monthly_eval.yaml --qrels-variant dctr --reuse-existing-run
python scripts/run_snapshot1_monthly_eval.py --config configs/custom_lexical_fulltext_temporal_citation.yaml --plan configs/plans/snapshot1_monthly_eval.yaml --qrels-variant dctr --reuse-existing-run
python scripts/run_snapshot1_monthly_eval.py --config configs/custom_title_abstract_rerank_temporal_citation.yaml --plan configs/plans/snapshot1_monthly_eval.yaml --qrels-variant dctr --reuse-existing-run
```

Rebuild the aggregate reports:

```powershell
python scripts/build_all_models_train_report.py
python scripts/build_monthly_split_summary.py
python scripts/build_temporal_change_report.py
```

## Current Evaluation Snapshot

On `snapshot-1 train` with `dctr` qrels:

- `custom_title_abstract_rerank_temporal_citation`
  - `nDCG@10 = 0.2562`
  - strongest citation-aware temporal variant in this pass, but still below `custom_title_abstract_rerank_temporal`
- `custom_lexical_fulltext_temporal_citation`
  - `nDCG@10 = 0.0088`
  - effectively unchanged from `custom_lexical_fulltext_temporal`
- `official_pyterrier_temporal_citation`
  - `nDCG@10 = 0.0046`
  - slightly worse on whole-train `nDCG@10`, though some monthly transitions improve

Interpretation:

- citation features alone do not fix an overly aggressive temporal rerank policy
- the reranked title+abstract branch remains the strongest citation-aware variant, but it still underperforms the non-citation temporal rerank sibling
- the next improvement should be weight tuning or intent-specific citation weighting, not more first-stage indexing
