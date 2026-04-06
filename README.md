# LongEval-Sci Run 1 Baselines

This repository is for **CLEF LongEval 2026 Task 1: LongEval-Sci**. The current focus is **Run 1**, a strong non-temporal baseline stack for longitudinal scientific retrieval.

Run 1 is meant to answer a simple but important question: before we add time-aware methods or update policies, how strong can a plain retrieval baseline be on the official LongEval-Sci benchmark?

## Benchmark Overview

LongEval-Sci is a **longitudinal scientific retrieval task**. Retrieval is evaluated on multiple corpus snapshots, so we care about both:

- retrieval quality on each snapshot
- how quality changes as the collection evolves

For LongEval 2026 Task 1, the scientific benchmark has three snapshots:

- `snapshot-1`: March to May 2025
- `snapshot-2`: June to August 2025
- `snapshot-3`: September to November 2025

`snapshot-1` includes training queries and qrels. Qrels are available in `raw` and `dctr` variants.

## Official Data Source

The default data backend in this repository is **`ir-datasets-longeval`**.

Example dataset ids:

- `longeval-sci-2026/snapshot-1`
- `longeval-sci-2026/snapshot-2`
- `longeval-sci-2026/snapshot-3`
- `longeval-sci-2026/clef-2026/sci`
- `longeval-sci-2026/clef-2026/rag`

The official loader API looks like:

```python
from ir_datasets_longeval import load

dataset = load("longeval-sci-2026/snapshot-3")
dataset.get_timestamp()
dataset.get_prior_datasets()
```

Local custom files are still supported for tests and offline integration work, but they are now a **secondary path** rather than the default execution mode.

## Official Baseline References

This repository is aligned with the official LongEval 2026 scientific retrieval baselines and reuses their naming conventions where practical:

- `clef-longeval/longeval-code/clef26/scientific-retrieval/baseline-pyterrier`
- `clef-longeval/longeval-code/clef26/scientific-retrieval/baseline-pyterrier-dense`

The goal here is not to clone those repositories line-for-line, but to keep baseline behavior, CLI expectations, and output layout close to the official setup while preserving a clean research-code structure.

## Repository Structure

- `src/longeval_sci/`: reusable library code
- `scripts/`: CLI entrypoints for dataset inspection, baseline runs, and evaluation
- `configs/`: baseline configs for official snapshots and local fixture-based tests
- `outputs/`: run files, per-snapshot metrics, and longitudinal reports
- `tests/`: fixture-based integration tests and optional official-loader smoke tests

## Quick Start

### 1. Install

```bash
pip install -e .
```

If you want the full official baseline stack:

```bash
pip install -r requirements.txt
```

### 2. Inspect an Official Dataset

```bash
python scripts/inspect_dataset.py --dataset longeval-sci-2026/snapshot-1 --qrels-variant dctr
```

This prints:

- document count
- query count
- whether qrels are available
- qrels variant
- timestamp if exposed by the dataset
- prior datasets if available

### 3. Run the Lexical Baseline

```bash
python scripts/run_baseline_pyterrier.py ^
  --dataset longeval-sci-2026/snapshot-1 ^
  --qrels-variant dctr ^
  --output-dir outputs/bm25_pt ^
  --index-dir indexes/bm25_pt
```

### 4. Run the Dense Baseline

```bash
python scripts/run_baseline_pyterrier_dense.py ^
  --dataset longeval-sci-2026/snapshot-1 ^
  --qrels-variant dctr ^
  --output-dir outputs/dense_pt ^
  --index-dir indexes/dense_pt ^
  --model-name intfloat/e5-base-v2
```

### 5. Run Dense + Rerank

```bash
python scripts/run_pipeline.py --config configs/dense_rerank.yaml --pipeline dense_rerank
```

### 6. Evaluate a Single Snapshot

```bash
python scripts/evaluate_run.py --config configs/bm25_pt.yaml
```

### 7. Evaluate Across Snapshots

```bash
python scripts/evaluate_longitudinal.py --runs-dir outputs/bm25_pt --qrels-variant dctr
```

## Configs

The primary configs are:

- `configs/bm25_pt.yaml`
- `configs/dense_pt.yaml`
- `configs/dense_rerank.yaml`

Each config now uses explicit fields for:

- `dataset_name`
- `snapshot_id`
- `qrels_variant`
- `output_dir`
- `index_dir`

There is also a local fixture config for offline tests:

- `configs/local_fixture_dense_rerank.yaml`

## Output Layout

Runs are organized by snapshot:

```text
outputs/
  bm25_pt/
    snapshot-1/
      run.txt
      metrics.json
      per_query_metrics.csv
    snapshot-2/
      run.txt
      metrics.json
      per_query_metrics.csv
    snapshot-3/
      run.txt
      metrics.json
      per_query_metrics.csv
    longitudinal_summary.json
    longitudinal_summary.csv
```

For final submission packaging, the runner can also write `run.txt.gz`.

## Current Scope

Current work is limited to **Run 1 strong baselines**:

- lexical baseline
- dense baseline
- dense + rerank extension
- per-snapshot evaluation
- cross-snapshot comparison

## Future Roadmap

- **Run 2**: time-aware retrieval and resilience-oriented methods
- **Run 3**: trigger and update-policy modeling

Those future runs are not implemented yet, but the dataset layer already exposes the official temporal hooks needed later.

## Troubleshooting

### `ir-datasets-longeval` missing

Install it with:

```bash
pip install ir-datasets-longeval
```

### PyTerrier setup issues

If `pyterrier` or Java is unavailable, the official-style runner names still work, but the current implementation falls back to the repository’s internal retrieval modules. This keeps development unblocked while staying aligned with the official baseline interfaces.

### FAISS missing

Dense retrieval falls back to a NumPy vector backend when FAISS is not installed.

### No qrels available

Some development settings or splits may not expose qrels. In that case the runner will still write a run file and will log that evaluation was skipped.

### CPU/GPU behavior

Dense retrieval and reranking default to CPU. You can pass `--device cuda` or set `runtime.device: cuda` in configs when the environment supports it.

## Testing

The default tests use tiny local fixtures under `tests/fixtures/` and do not require network access.

An additional smoke test uses the official dataset loader and is skipped automatically when `ir-datasets-longeval` is not installed.

## References

- LongEval task page: https://clef-longeval.github.io/tasks/
- Official scientific retrieval baselines: https://github.com/clef-longeval/longeval-code/tree/main/clef26/scientific-retrieval
- `ir-datasets-longeval`: https://pypi.org/project/ir-datasets-longeval/
