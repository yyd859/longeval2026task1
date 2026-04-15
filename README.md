# LongEval-Sci Baseline Platform

This repository is our working platform for **CLEF LongEval 2026 Task 1: LongEval-Sci**.

The project is organized around a simple development protocol:

- use **`snapshot-1 train`** as the main supervised development split
- treat **later snapshots** as temporal evaluation conditions
- keep **Run 1** focused on non-temporal improvements
- add **Run 2** temporal features as clean overlays on top of existing runs

Official references:

- LongEval task page: https://clef-longeval.github.io/tasks/
- Official baseline code: https://github.com/clef-longeval/longeval-code/tree/main/clef26/scientific-retrieval

Useful project notes:

- [MODEL_OVERVIEW.md](c:/Users/Will/Documents/longEval2026task1/MODEL_OVERVIEW.md)
- [TEMPORAL_FEATURES_DESIGN.md](c:/Users/Will/Documents/longEval2026task1/TEMPORAL_FEATURES_DESIGN.md)
- [TEMPORAL_CITATION_FEATURES.md](c:/Users/Will/Documents/longEval2026task1/TEMPORAL_CITATION_FEATURES.md)
- [TEMPORAL_METRICS.md](c:/Users/Will/Documents/longEval2026task1/TEMPORAL_METRICS.md)
- [MIGRATION.md](c:/Users/Will/Documents/longEval2026task1/MIGRATION.md)

## Current Model Set

We currently track **16 models** in four families.

Base models:

- `official_pyterrier`
- `official_pyterrier_dense`
- `custom_lexical_fulltext`
- `custom_title_abstract_rm3`
- `custom_title_abstract_rerank`

Temporal sibling models:

- `official_pyterrier_temporal`
- `official_pyterrier_dense_temporal`
- `custom_lexical_fulltext_temporal`
- `custom_title_abstract_rm3_temporal`
- `custom_title_abstract_rerank_temporal`

Fusion models:

- `rrf_bm25_ta_dense_ta`
- `rrf_bm25_ft_dense_ta`
- `rrf_bm25_ta_bm25_ft_dense_ta`

Citation-aware temporal models:

- `official_pyterrier_temporal_citation`
- `custom_lexical_fulltext_temporal_citation`
- `custom_title_abstract_rerank_temporal_citation`

Design-level descriptions live in [MODEL_OVERVIEW.md](c:/Users/Will/Documents/longEval2026task1/MODEL_OVERVIEW.md).

## Current Findings

Main shareable reports:

- [whole-train summary](c:/Users/Will/Documents/longEval2026task1/outputs/reports/all_models_train_snapshot1/summary.md)
- [monthly growth summary](c:/Users/Will/Documents/longEval2026task1/outputs/reports/monthly_split/_summary/monthly_comparison.md)
- [temporal change summary](c:/Users/Will/Documents/longEval2026task1/outputs/reports/monthly_split/_summary/temporal_change/temporal_change.md)

Current picture:

- strongest base model on `snapshot-1 train`: `custom_lexical_fulltext`
- strongest fusion model so far: `rrf_bm25_ft_dense_ta`
- strongest temporal sibling so far: `official_pyterrier_dense_temporal`
- strongest citation-aware temporal sibling so far: `custom_title_abstract_rerank_temporal_citation`
- several temporal siblings are currently too aggressive and need tuning:
  - `official_pyterrier_temporal`
  - `custom_lexical_fulltext_temporal`
  - `custom_title_abstract_rm3_temporal`

Citation-feature takeaway from the current pass:

- citation effects are mixed rather than uniformly helpful
- `official_pyterrier_temporal_citation` improves some month-growth transitions relative to `official_pyterrier_temporal`, but not the whole-train headline score
- `custom_lexical_fulltext_temporal_citation` is effectively unchanged from `custom_lexical_fulltext_temporal`
- `custom_title_abstract_rerank_temporal_citation` is the strongest citation-aware sibling, but it still underperforms `custom_title_abstract_rerank_temporal`

Official reference note:

- organizer-provided BM25 and Qwen train runs are kept under `outputs/baseline_reference/`
- the report builders treat those as fixed anchors, so they do not need to be rerun just to refresh summaries

## Data and Evaluation Protocol

Important split distinction:

- `snapshot-1 train`
  - full `snapshot-1` document collection
  - train queries
  - train qrels
- `snapshot-1`, `snapshot-2`, `snapshot-3`
  - official snapshot runs
  - later snapshots are temporal evaluation conditions

So local model development happens on the full `snapshot-1` corpus with a train-only query/qrel split.

## Canonical Indices

We keep the first-stage index inventory deliberately small.

Canonical text views:

1. `title_abstract`
2. `fulltext`

Canonical index locations:

```text
indexes/
  snapshot-1/
    title_abstract/
      lexical_pyterrier/
      dense/
        intfloat_e5-base-v2/
      official_dense/
        Qwen_Qwen3-Embedding-4B/
    fulltext/
      lexical_pyterrier/
```

Rules:

- lexical and dense remain separate backends even when they use similar text
- RM3, reranking, temporal overlay, and RRF fusion should reuse existing first-stage artifacts
- we do not rebuild indices just to apply fusion or temporal reranking

## Evaluation Layers

We use three complementary evaluation layers.

### 1. Whole-Train Evaluation

Purpose:

- absolute effectiveness on `snapshot-1 train`

Main outputs:

- [summary.md](c:/Users/Will/Documents/longEval2026task1/outputs/reports/all_models_train_snapshot1/summary.md)
- [comparison_all.csv](c:/Users/Will/Documents/longEval2026task1/outputs/reports/all_models_train_snapshot1/comparison_all.csv)

### 2. Monthly Split Evaluation

Purpose:

- robustness as the simulated corpus grows from March to May

Current cumulative splits:

- `march_only`
- `march_april`
- `march_april_may`

Main outputs:

- [monthly_comparison.md](c:/Users/Will/Documents/longEval2026task1/outputs/reports/monthly_split/_summary/monthly_comparison.md)
- [monthly_comparison.csv](c:/Users/Will/Documents/longEval2026task1/outputs/reports/monthly_split/_summary/monthly_comparison.csv)

### 3. Temporal Change Evaluation

Purpose:

- RI / DRI / ER / ARP / MARP relative to the BM25 pivot

Current pivot:

- `official_pyterrier_dctr`

Main outputs:

- [temporal_change.md](c:/Users/Will/Documents/longEval2026task1/outputs/reports/monthly_split/_summary/temporal_change/temporal_change.md)
- [temporal_change.csv](c:/Users/Will/Documents/longEval2026task1/outputs/reports/monthly_split/_summary/temporal_change/temporal_change.csv)

## Canonical Scripts

Main scripts we actively use:

- `scripts/check_official_env.py`
- `scripts/build_indices.py`
- `scripts/run_baseline.py`
- `scripts/run_all_baselines.py`
- `scripts/run_rrf_fusion.py`
- `scripts/run_temporal_overlay.py`
- `scripts/run_snapshot1_monthly_eval.py`
- `scripts/build_all_models_train_report.py`
- `scripts/build_monthly_split_summary.py`
- `scripts/build_temporal_change_report.py`
- `scripts/pipeline.ipynb`

Optional analysis script:

- `scripts/run_rerank_sweep_train_snapshot1.py`

## Environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

For PyTerrier:

```powershell
$env:JAVA_HOME="C:\Program Files\Java\jdk-17"
$env:Path="$env:JAVA_HOME\bin;$env:Path"
```

Preflight:

```powershell
python scripts/check_official_env.py
```

## Main Commands

Build needed indices for a config:

```powershell
python scripts/build_indices.py --config configs/custom_lexical_fulltext.yaml
```

Run one model on `snapshot-1 train`:

```powershell
python scripts/run_baseline.py --config configs/custom_lexical_fulltext.yaml --train-snapshot1 --qrels-variant dctr
python scripts/run_baseline.py --config configs/custom_title_abstract_rm3.yaml --train-snapshot1 --qrels-variant dctr
python scripts/run_baseline.py --config configs/custom_title_abstract_rerank.yaml --train-snapshot1 --qrels-variant dctr
```

Apply temporal overlays without rebuilding retrieval:

```powershell
python scripts/run_baseline.py --config configs/official_pyterrier_temporal.yaml --train-snapshot1 --qrels-variant dctr
python scripts/run_baseline.py --config configs/official_pyterrier_dense_temporal.yaml --train-snapshot1 --qrels-variant dctr
python scripts/run_baseline.py --config configs/custom_lexical_fulltext_temporal.yaml --train-snapshot1 --qrels-variant dctr
python scripts/run_baseline.py --config configs/custom_title_abstract_rm3_temporal.yaml --train-snapshot1 --qrels-variant dctr
python scripts/run_baseline.py --config configs/custom_title_abstract_rerank_temporal.yaml --train-snapshot1 --qrels-variant dctr
```

Apply citation-aware temporal overlays on top of existing train runs:

```powershell
python scripts/run_temporal_overlay.py --config configs/official_pyterrier_temporal_citation.yaml --input-run outputs/official_pyterrier/snapshot-1-train/run.txt --train-snapshot1 --qrels-variant dctr
python scripts/run_temporal_overlay.py --config configs/custom_lexical_fulltext_temporal_citation.yaml --input-run outputs/custom_lexical_fulltext/snapshot-1-train/run.txt --train-snapshot1 --qrels-variant dctr
python scripts/run_temporal_overlay.py --config configs/custom_title_abstract_rerank_temporal_citation.yaml --input-run outputs/custom_title_abstract_rerank/snapshot-1-train/run.txt --train-snapshot1 --qrels-variant dctr
```

Then evaluate those citation-aware temporal runs with the same monthly and temporal-change pipeline:

```powershell
python scripts/run_snapshot1_monthly_eval.py --config configs/official_pyterrier_temporal_citation.yaml --plan configs/plans/snapshot1_monthly_eval.yaml --qrels-variant dctr --reuse-existing-run
python scripts/run_snapshot1_monthly_eval.py --config configs/custom_lexical_fulltext_temporal_citation.yaml --plan configs/plans/snapshot1_monthly_eval.yaml --qrels-variant dctr --reuse-existing-run
python scripts/run_snapshot1_monthly_eval.py --config configs/custom_title_abstract_rerank_temporal_citation.yaml --plan configs/plans/snapshot1_monthly_eval.yaml --qrels-variant dctr --reuse-existing-run
python scripts/build_all_models_train_report.py
python scripts/build_monthly_split_summary.py
python scripts/build_temporal_change_report.py
```

Build RRF fusion runs from existing run files:

```powershell
python scripts/run_rrf_fusion.py --run-name rrf_bm25_ta_dense_ta --input-run outputs/official_pyterrier/snapshot-1-train/run.txt --input-run outputs/official_pyterrier_dense/snapshot-1-train/run.txt --train-snapshot1 --qrels-variant dctr
python scripts/run_rrf_fusion.py --run-name rrf_bm25_ft_dense_ta --input-run outputs/custom_lexical_fulltext/snapshot-1-train/run.txt --input-run outputs/official_pyterrier_dense/snapshot-1-train/run.txt --train-snapshot1 --qrels-variant dctr
python scripts/run_rrf_fusion.py --run-name rrf_bm25_ta_bm25_ft_dense_ta --input-run outputs/official_pyterrier/snapshot-1-train/run.txt --input-run outputs/custom_lexical_fulltext/snapshot-1-train/run.txt --input-run outputs/official_pyterrier_dense/snapshot-1-train/run.txt --train-snapshot1 --qrels-variant dctr
```

Rebuild the three main reports:

```powershell
python scripts/build_all_models_train_report.py
python scripts/build_monthly_split_summary.py
python scripts/build_temporal_change_report.py
```

Run monthly split evaluation on existing runs:

```powershell
python scripts/run_snapshot1_monthly_eval.py --config configs/official_pyterrier.yaml --plan configs/plans/snapshot1_monthly_eval.yaml --qrels-variant dctr --reuse-existing-run
python scripts/run_snapshot1_monthly_eval.py --config configs/official_pyterrier_dense.yaml --plan configs/plans/snapshot1_monthly_eval.yaml --qrels-variant dctr --reuse-existing-run
python scripts/run_snapshot1_monthly_eval.py --config configs/custom_lexical_fulltext.yaml --plan configs/plans/snapshot1_monthly_eval.yaml --qrels-variant dctr --reuse-existing-run
python scripts/run_snapshot1_monthly_eval.py --config configs/custom_title_abstract_rm3.yaml --plan configs/plans/snapshot1_monthly_eval.yaml --qrels-variant dctr --reuse-existing-run
python scripts/run_snapshot1_monthly_eval.py --config configs/custom_title_abstract_rerank.yaml --plan configs/plans/snapshot1_monthly_eval.yaml --qrels-variant dctr --reuse-existing-run
```

Then rebuild the monthly and temporal-change summaries:

```powershell
python scripts/build_monthly_split_summary.py
python scripts/build_temporal_change_report.py
```

## Output Layout

Outputs are model-centric:

```text
outputs/
  <model_name>/
    snapshot-1/
    snapshot-1-train/
    snapshot-2/
    snapshot-3/
  reports/
    all_models_train_snapshot1/
    monthly_split/
      <model>_<qrels_variant>/
      _summary/
```

For snapshots without released qrels:

- `run.txt` is the main artifact
- `metrics.json` records skipped evaluation

For train and month-based evaluation:

- metrics are saved normally
- reports live under `outputs/reports/`

## Notebook

For a quick teammate-oriented walkthrough, use:

- [scripts/pipeline.ipynb](c:/Users/Will/Documents/longEval2026task1/scripts/pipeline.ipynb)

It is designed as a catch-up notebook for:

- rebuilding the three main reports
- reviewing current findings
- optionally rerunning the monthly and temporal summary steps
