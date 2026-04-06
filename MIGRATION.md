# Migration Note

## What Changed

- The repository is now **official-dataset-first**.
- Default execution uses `ir-datasets-longeval` instead of local toy files.
- Baseline runner names now align with the official LongEval baselines:
  - `bm25_pt`
  - `dense_pt`
  - `dense_rerank`
- Outputs are now organized per snapshot under a run root such as `outputs/bm25_pt/snapshot-1/run.txt`.
- Tiny synthetic data moved from `data/` to `tests/fixtures/`.
- Longitudinal evaluation now produces JSON and CSV summaries across `snapshot-1`, `snapshot-2`, and `snapshot-3`.

## How To Run The New Pipeline

Inspect a dataset:

```bash
python scripts/inspect_dataset.py --dataset longeval-sci-2026/snapshot-1 --qrels-variant dctr
```

Run the lexical baseline:

```bash
python scripts/run_baseline_pyterrier.py --dataset longeval-sci-2026/snapshot-1 --output-dir outputs/bm25_pt --index-dir indexes/bm25_pt
```

Run the dense baseline:

```bash
python scripts/run_baseline_pyterrier_dense.py --dataset longeval-sci-2026/snapshot-1 --output-dir outputs/dense_pt --index-dir indexes/dense_pt
```

Run dense + rerank from config:

```bash
python scripts/run_pipeline.py --config configs/dense_rerank.yaml --pipeline dense_rerank
```

Evaluate across snapshots:

```bash
python scripts/evaluate_longitudinal.py --runs-dir outputs/bm25_pt --qrels-variant dctr
```

## What Remains For Later Runs

- explicit temporal scoring
- citation-aware retrieval features
- historical query reuse
- query clustering transfer
- trigger and update-policy models

Those remain future work for Run 2 and Run 3.
