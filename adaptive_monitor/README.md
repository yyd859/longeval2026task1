# adaptive_monitor

Monitoring and daily-split evaluation for the chosen production model: `custom_lexical_fulltext` (BM25 full text).

Does NOT modify any other folder. Reuses existing source code from `src/` and configs from `configs/`.

## Scripts

### `collection_analytics.py`
Runs from document metadata only. No run.txt required.

Outputs:
- `outputs/collection_analytics/daily_doc_counts.csv` — new docs and cumulative count per day
- `outputs/collection_analytics/weekly_doc_counts.csv` — same, aggregated by week
- `outputs/collection_analytics/staleness_rate.csv` — Doc Staleness Rate per weekly cutoff
- `outputs/collection_analytics/temporal_gap.csv` — Temporal Gap per weekly cutoff
- `outputs/collection_analytics/summary.json` — top-level summary stats

Run:
    python adaptive_monitor/collection_analytics.py

### `trigger_decision.py`
Reads `collection_analytics.py` outputs and computes weekly reindex trigger decisions.

Implemented trigger rules:
- Level 1 soft alert:
  - `Doc Staleness Rate > 15%`
  - and `Index Coverage Gap > 5%`
- Level 2 incremental reindex candidate:
  - `Temporal Gap growth > 30 days`
  - or `New Doc Velocity > 2x baseline`
- Level 3 full rebuild candidate:
  - optional `rank_stability_drop > 20%` for 3 consecutive periods, if a rank-stability CSV is supplied

Outputs:
- `outputs/reindex_pipeline/trigger_decisions.csv`
- `outputs/reindex_pipeline/trigger_decisions.json`

Run:
    python adaptive_monitor/trigger_decision.py

### `reindex_pipeline.py`
Runs the adaptive reindex pipeline around the trigger decisions.

Default mode is plan-only. It writes a manifest and does not touch live indexes:

    python adaptive_monitor/reindex_pipeline.py --mode plan

Build mode creates a shadow index under:

    adaptive_monitor/outputs/reindex_pipeline/runs/<run_id>/shadow_indexes/

Run:
    python adaptive_monitor/reindex_pipeline.py --mode build --last-reindex-week 2025-03-03

For Level 2 decisions, build mode now uses an incremental lexical path by default:

1. build a delta PyTerrier index for documents with `date_field` after `--last-reindex-week`
2. merge the live canonical index and delta index into the shadow index
3. write an incremental manifest under `runs/<run_id>/incremental/`

The incremental path is implemented for lexical PyTerrier pipelines. Use
`--full-rebuild` to build a complete shadow index instead:

    python adaptive_monitor/reindex_pipeline.py --mode build --full-rebuild

Promotion is explicit and disabled by default:

    python adaptive_monitor/reindex_pipeline.py --mode build --last-reindex-week 2025-03-03 --promote

Notes:
- Level 1 only logs a soft alert unless `--force-build` is passed.
- Dense Qwen indexes are treated as Level 3 only unless `--force-build` is passed.
- Incremental lexical reindexing builds and merges a delta index; it does not mutate the live index in place.

### `daily_split_eval.py`
Requires `outputs/custom_lexical_fulltext/snapshot-1-train/run.txt`.
Computes nDCG@10, MAP, Recall@100, Recall@1000 for each cumulative daily window.

Run:
    python adaptive_monitor/daily_split_eval.py --step-days 7

To regenerate the run file first:
    python scripts/run_baseline.py \
        --config configs/custom_lexical_fulltext.yaml \
        --snapshot-id snapshot-1 \
        --train-snapshot1

## What each script tells you

| Script | Tells you |
| --- | --- |
| `collection_analytics.py` | How fast new documents arrive, how stale the index becomes over time |
| `trigger_decision.py` | Which weekly cutoffs cross Level 1/2/3 reindex thresholds |
| `reindex_pipeline.py` | Plans or builds a shadow reindex run from the latest actionable trigger |
| `daily_split_eval.py` | How nDCG@10 and recall change as more documents are added to the evaluation window |
