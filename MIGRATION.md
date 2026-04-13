# Migration Note

## What Was Removed

- per-model wrapper scripts such as old `run_custom_*.py` and `run_official_*.py`
- older one-off report builders:
  - `build_train_snapshot1_report.py`
  - `build_rrf_train_snapshot1_report.py`
- stale exploratory output folders:
  - `outputs/custom_dense_rerank/`
  - `outputs/custom_hybrid_union_rerank/`
  - `outputs/custom_hybrid_rrf_rerank/`

## What Changed

- the repo now centers on a smaller generic workflow:
  - `build_indices.py`
  - `run_baseline.py`
  - `run_all_baselines.py`
  - `run_rrf_fusion.py`
  - `run_temporal_overlay.py`
  - `run_snapshot1_monthly_eval.py`
  - `build_all_models_train_report.py`
  - `build_monthly_split_summary.py`
  - `build_temporal_change_report.py`
  - `check_official_env.py`
  - `pipeline.ipynb`
- configs are grouped under:
  - `configs/base/`
  - `configs/temporal/`
  - `configs/plans/`
  while top-level config files remain as compatibility wrappers
- the active comparison set is now broader than the original five-model setup:
  - 5 base models
  - 5 temporal sibling models
  - 3 RRF fusion models
- index usage is now organized around canonical text views instead of per-model duplication
- month-based evaluation is now a filtered evaluation layer on top of existing runs
- temporal-change reporting now reads from the unified monthly summary

## Canonical Commands

Build or reuse indices:

```powershell
python scripts/build_indices.py --config configs/custom_lexical_fulltext.yaml
```

Run one model on `snapshot-1 train`:

```powershell
python scripts/run_baseline.py --config configs/custom_lexical_fulltext.yaml --train-snapshot1 --qrels-variant dctr
python scripts/run_baseline.py --config configs/custom_title_abstract_rm3.yaml --train-snapshot1 --qrels-variant dctr
python scripts/run_baseline.py --config configs/custom_title_abstract_rerank.yaml --train-snapshot1 --qrels-variant dctr
```

Build RRF fusion runs from existing outputs:

```powershell
python scripts/run_rrf_fusion.py --run-name rrf_bm25_ta_dense_ta --input-run outputs/official_pyterrier/snapshot-1-train/run.txt --input-run outputs/official_pyterrier_dense/snapshot-1-train/run.txt --train-snapshot1 --qrels-variant dctr
python scripts/run_rrf_fusion.py --run-name rrf_bm25_ft_dense_ta --input-run outputs/custom_lexical_fulltext/snapshot-1-train/run.txt --input-run outputs/official_pyterrier_dense/snapshot-1-train/run.txt --train-snapshot1 --qrels-variant dctr
python scripts/run_rrf_fusion.py --run-name rrf_bm25_ta_bm25_ft_dense_ta --input-run outputs/official_pyterrier/snapshot-1-train/run.txt --input-run outputs/custom_lexical_fulltext/snapshot-1-train/run.txt --input-run outputs/official_pyterrier_dense/snapshot-1-train/run.txt --train-snapshot1 --qrels-variant dctr
```

Rebuild reports:

```powershell
python scripts/build_all_models_train_report.py
python scripts/build_monthly_split_summary.py
python scripts/build_temporal_change_report.py
```

## Canonical Index Locations

```text
indexes/
  snapshot-1/
    title_abstract/
      lexical_pyterrier/
      dense/
      official_dense/
    fulltext/
      lexical_pyterrier/
```

RM3, reranking, temporal overlays, and RRF fusion are overlays on top of these first-stage artifacts. They should not trigger fresh indexing unless the underlying retrieval representation changes.
