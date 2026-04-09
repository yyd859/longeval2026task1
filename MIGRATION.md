# Migration Note

## What Was Removed

- redundant helper scripts for partial pipeline steps
- redundant and test-only configs from `configs/`
- the `data/` smoke-data workflow
- one-snapshot-first evaluation assumptions

Tiny synthetic data remains only under `tests/fixtures/`.

## What Changed

- the repository now centers on **five canonical baselines**
- each baseline runs across **snapshot-1**, **snapshot-2**, and **snapshot-3** by default
- outputs are organized per method and per snapshot
- the consolidated report now includes machine-readable files and a human-readable comparison table
- the repo uses a project-local `.venv` and workspace-local `ir_datasets` cache

## New Canonical Commands

Run all five baselines across all three snapshots:

```powershell
python scripts/run_all_baselines.py
```

Run one baseline:

```powershell
python scripts/run_official_pyterrier.py
python scripts/run_official_pyterrier_dense.py
python scripts/run_custom_lexical_fulltext.py
python scripts/run_custom_dense_rerank.py
python scripts/run_custom_hybrid_union_rerank.py
```

Run the tests:

```powershell
.\.venv\Scripts\python.exe -m unittest discover tests
```

## How The New Workflow Works

1. Each baseline config defines one method.
2. The runner executes that method across all three official snapshots.
3. Each snapshot gets its own `run.txt`, `metrics.json`, and `per_query_metrics.csv`.
4. The suite runner writes a consolidated comparison report across methods and snapshots.
