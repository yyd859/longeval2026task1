# LongEval-Sci Baseline Platform

This repository is for **CLEF LongEval 2026 Task 1: LongEval-Sci**. It is a research baseline platform for:

- reproducing the official lexical and dense baselines
- building stronger custom baselines on top of them
- comparing methods across evolving corpus snapshots
- keeping the codebase ready for later Run 2 and Run 3 work

Current shareable report:

- [train summary](c:/Users/Will/Documents/longEval2026task1/outputs/reports/train_snapshot1/summary.md)
- [model overview](c:/Users/Will/Documents/longEval2026task1/MODEL_OVERVIEW.md)

## Benchmark Overview

LongEval-Sci is a **longitudinal scientific retrieval** task over three corpus snapshots:

- `snapshot-1`
- `snapshot-2`
- `snapshot-3`

The official task also provides a **snapshot-1 train split** with train queries and qrels. That train split is what we currently use for local metric-based comparison.

Two qrel variants are available:

- `raw`: clicked documents are marked relevant
- `dctr`: pseudo relevance labels derived from Document Click Through Rate

In the current local train files:

- `raw` is binary positive-only qrels
- `dctr` contains graded labels `0`, `1`, and `2`

That matters because:

- `nDCG` uses graded relevance directly
- `MAP` and `Recall` treat relevance values `> 0` as relevant

## Baselines

The current baseline set is:

Official-anchor baselines:

1. `official_pyterrier`
2. `official_pyterrier_dense`

Custom baselines:

3. `custom_lexical_fulltext`
4. `custom_dense_rerank`
5. `custom_hybrid_union_rerank`

Mapping to the official LongEval references:

- `official_pyterrier` = the official **BM25** baseline
- `official_pyterrier_dense` = the official **Qwen3-Embedding-4B** dense baseline

The lexical baseline is reproduced locally. The official dense baseline still requires the local embedding service expected by the upstream baseline script.

For a design-focused explanation of the five models, see [MODEL_OVERVIEW.md](c:/Users/Will/Documents/longEval2026task1/MODEL_OVERVIEW.md).

Short version:

- `official_pyterrier`: official BM25 lexical anchor
- `official_pyterrier_dense`: official dense Qwen anchor
- `custom_lexical_fulltext`: stronger sparse baseline using full text
- `custom_dense_rerank`: dense retrieval followed by reranking
- `custom_hybrid_union_rerank`: lexical+dense candidate union followed by reranking

## Data Layout

The active local cache layout is:

```text
.cache/ir_datasets/longeval-sci-2026/
  snapshot1/
  snapshot2/
  snapshot3/
  longeval_adhoc-queries-snapshot-test.tsv
  task1_longeval_adhoc-queries-snapshot-train.tsv
  task1_longeval_adhoc-qrels-snapshot-train-dctr.txt
  task1_longeval_adhoc-qrels-snapshot-train-raw.txt
```

The code now supports:

- abstract-based snapshot loading
- fulltext-aware local snapshot loading
- train-split evaluation on `snapshot-1`

Important split distinction:

- `snapshot-1-train` is the local development split with train queries and qrels
- `snapshot-1`, `snapshot-2`, and `snapshot-3` are the official test snapshots
- test snapshots currently produce ranking files, but local metrics stay empty until test qrels are released

## Environment

Create the local environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

For PyTerrier, make sure Java 17 is active:

```powershell
$env:JAVA_HOME="C:\Program Files\Java\jdk-17"
$env:Path="$env:JAVA_HOME\bin;$env:Path"
java -version
```

Preflight check:

```powershell
python scripts/check_official_env.py
```

## Canonical Commands

Official lexical baseline over the three test snapshots:

```powershell
python scripts/run_official_pyterrier.py
```

Official dense baseline over the three test snapshots:

```powershell
python scripts/run_official_pyterrier_dense.py
```

Custom baselines:

```powershell
python scripts/run_custom_lexical_fulltext.py
python scripts/run_custom_dense_rerank.py
python scripts/run_custom_hybrid_union_rerank.py
```

All five:

```powershell
python scripts/run_all_baselines.py
```

## Output Layout

Outputs are now model-centric:

```text
outputs/
  official_pyterrier/
    snapshot-1/
      run.txt
      metrics.json
      per_query_metrics.csv
    snapshot-1-train/
      run.txt
      metrics.json
      per_query_metrics.csv
    snapshot-2/
      ...
    snapshot-3/
      ...
  custom_lexical_fulltext/
    snapshot-1-train/
      ...
  custom_dense_rerank/
    snapshot-1-train/
      ...
  custom_hybrid_union_rerank/
    snapshot-1-train/
      ...
  baseline_reference/
    ...
  reports/
    train_snapshot1/
      summary.md
      comparison_dctr.csv
      comparison_raw.csv
      comparison_all.csv
```

For test snapshots without released qrels:

- `run.txt` is the important artifact
- `metrics.json` is written with `status = skipped`

For train evaluation:

- metrics are written normally
- train outputs now live under the same model directories, for example:
  - `outputs/official_pyterrier/snapshot-1-train/`
  - `outputs/custom_lexical_fulltext/snapshot-1-train/`

## Current Train Findings

Train comparison report:

- [summary.md](c:/Users/Will/Documents/longEval2026task1/outputs/reports/train_snapshot1/summary.md)
- [comparison_dctr.csv](c:/Users/Will/Documents/longEval2026task1/outputs/reports/train_snapshot1/comparison_dctr.csv)
- [comparison_raw.csv](c:/Users/Will/Documents/longEval2026task1/outputs/reports/train_snapshot1/comparison_raw.csv)

Snapshot-1 train, DCTR qrels:

| Method | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `official_pyterrier` | 0.2922 | 0.4564 | 0.2573 | 0.6836 | 0.8581 |
| `reference_qwen3` | 0.2820 | 0.4483 | 0.2378 | 0.6390 | 0.8613 |
| `custom_lexical_fulltext` | 0.3302 | 0.5077 | 0.2853 | 0.7394 | 0.9245 |
| `custom_dense_rerank` | 0.1284 | 0.1686 | 0.0853 | 0.2925 | 0.3106 |
| `custom_hybrid_union_rerank` | 0.1371 | 0.3580 | 0.1245 | 0.5316 | 0.9388 |

Takeaway:

- the custom fulltext lexical run is currently the strongest model on the train split
- the official BM25 run matches the downloaded official BM25 reference
- the current dense and hybrid custom runs need more tuning

## Qrels Interpretation

We currently report train metrics under both `dctr` and `raw` qrels.

How to read them:

- `raw` asks a simpler question: did we retrieve clicked documents?
- `dctr` asks a more nuanced question: did we rank stronger pseudo-relevant documents above weaker ones?

That means:

- `nDCG` is usually the most informative metric for `dctr`
- `MAP` and `Recall` are still useful, but they collapse graded labels into relevant vs not relevant

If you are discussing the current baseline quality in a paper draft or lab note, prefer the `dctr` table first and use the `raw` table as a robustness check.

## What Has Been Done

Recent work completed in this repo:

- aligned the official lexical path with the upstream PyTerrier baseline
- mapped the official dense baseline to the upstream Qwen design
- added local snapshot-cache loading for abstract and fulltext corpora
- added train-split evaluation support for `snapshot-1`
- added parsing for the provided train qrels text files
- generated a comparable train report across official BM25, official Qwen reference, and the three custom baselines
- cleaned output naming so future official runs write plain `run.txt`
- reorganized outputs so train results sit under each model directory
- kept shareable reports under `outputs/reports/train_snapshot1/`

## Notes on the Official Dense Baseline

The upstream official dense baseline expects:

- `Qwen/Qwen3-Embedding-4B`
- an OpenAI-compatible local service at `http://localhost:6543/v1`

So `official_pyterrier_dense` will not run end to end until that service is available.

## Testing

Run the local tests:

```powershell
.\.venv\Scripts\python.exe -m unittest discover tests
```

## Roadmap

Current scope:

- strong Run 1 baselines
- official baseline alignment
- snapshot-aware outputs
- train/test split-aware evaluation

Later:

- Run 2 time-aware retrieval
- Run 3 trigger/update policies
