"""Three-scenario nDCG@10 comparison for BM25 fulltext on snapshot-1.

Scenario 1 — no_reindex:
    Index fixed at baseline (publishedDate < WINDOW_START).
    New documents cannot be retrieved even as time passes.

Scenario 2 — append_reindex:
    Each step adds newly published docs to the index incrementally.
    Simulated by filtering run.txt to docs with publishedDate <= cutoff.

Scenario 3 — global_reindex:
    Full rebuild at each step. For a static dataset, identical to append
    (same final doc set, IDF computed on full corpus approximation).

Qrels are fixed to all relevant docs within the evaluation window so all
three scenarios are evaluated on the same relevance judgments.

Usage:
    python adaptive_monitor/scenario_comparison.py --step-days 7
    python adaptive_monitor/scenario_comparison.py --step-days 1
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from longeval_sci.baselines.runner import clone_for_train_eval
from longeval_sci.config import load_config
from longeval_sci.evaluation.pytrec_eval_wrapper import evaluate_run_dict
from longeval_sci.io.dataset import load_dataset_bundle
from longeval_sci.io.trec import read_trec_run

METRICS = ["ndcg_cut_10", "ndcg_cut_1000", "map", "recall_100", "recall_1000"]
CONFIG_PATH = ROOT / "configs" / "custom_lexical_fulltext.yaml"
SNAPSHOT_ID = "snapshot-1"
DATE_FIELD = "publishedDate"

WINDOW_START = datetime(2025, 3, 1, tzinfo=UTC)
WINDOW_END = datetime(2025, 5, 31, 23, 59, 59, tzinfo=UTC)
BASELINE_CUTOFF = WINDOW_START - timedelta(seconds=1)  # 2025-02-28T23:59:59


def _parse_dt(value: object) -> datetime | None:
    """
    Convert a value to a UTC-aware datetime or return None when the input is missing or cannot be parsed.
    
    Parameters:
        value (object): A datetime-like value (commonly an ISO-8601 string, possibly ending with 'Z'). If the value is None or empty, the function returns None.
    
    Returns:
        datetime | None: A timezone-aware `datetime` normalized to UTC when parsing succeeds, or `None` if the input is falsy or unparsable.
    """
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except ValueError:
        return None


def _doc_ids_by_cutoff(bundle, cutoff: datetime) -> set[str]:
    """
    Collect document IDs whose `publishedDate` is less than or equal to a cutoff.
    
    Parameters:
        bundle: An object with a `documents` iterable; each document must have `doc_id` and a `metadata` mapping containing the date field defined by `DATE_FIELD`.
        cutoff (datetime): A timezone-aware datetime used as the inclusive upper bound for `publishedDate`.
    
    Returns:
        set[str]: Set of document IDs with a parsed `publishedDate` that is not None and is <= `cutoff`.
    """
    return {
        doc.doc_id
        for doc in bundle.documents
        if (dt := _parse_dt(doc.metadata.get(DATE_FIELD))) is not None and dt <= cutoff
    }


def _filter_run(run: dict, allowed_docs: set[str], allowed_qids: set[str]) -> dict:
    """
    Filter a TREC run to retain only specified queries and documents.
    
    Parameters:
        run (dict): Mapping from query id to a mapping of document id to score (run[qid][docid] = score).
        allowed_docs (set[str]): Document ids that should be kept in each query's results.
        allowed_qids (set[str]): Query ids that should be retained in the returned run.
    
    Returns:
        dict: A filtered run dictionary containing only query ids in `allowed_qids`, where each query maps
        to a dict of its documents whose ids are in `allowed_docs`.
    """
    return {
        qid: {d: s for d, s in docs.items() if d in allowed_docs}
        for qid, docs in run.items()
        if qid in allowed_qids
    }


def _eval(qrels: dict, run: dict) -> dict[str, float]:
    """
    Compute aggregated metrics for a TREC run against provided qrels.
    
    Parameters:
        qrels (dict): Query relevance judgments mapping query id to a mapping of document id to relevance (e.g., {qid: {docid: int}}). If empty or falsy, the function returns zeros for all configured metrics.
        run (dict): Retrieved run mapping query id to a mapping of document id to score (e.g., {qid: {docid: float}}).
    
    Returns:
        dict[str, float]: Mapping from metric name to its aggregated value (float) for the configured METRICS. If `qrels` is falsy, returns 0.0 for each metric.
    """
    if not qrels:
        return {m: 0.0 for m in METRICS}
    aggregate, _ = evaluate_run_dict(qrels, run, METRICS)
    return aggregate


def run_comparison(run_path: Path, step_days: int) -> list[dict]:
    """
    Compare three reindexing scenarios over successive time cutoffs using a TREC run and the dataset bundle for SNAPSHOT_ID.
    
    This function repeatedly filters the provided run by document publication date at incremental cutoffs and evaluates three scenarios — no_reindex (fixed baseline index), append_reindex (cumulative index up to the cutoff), and global_reindex (treated equivalent to append_reindex for this dataset) — computing aggregated metrics for each cutoff.
    
    Parameters:
        run_path (Path): Path to the TREC run file to evaluate.
        step_days (int): Number of days between successive cutoff points (controls cutoff increment).
    
    Returns:
        list[dict]: A list of per-cutoff result records. Each record contains:
            - "cutoff_date" (str): cutoff in "YYYY-MM-DD" format.
            - "days_since_start" (int): days elapsed since WINDOW_START (inclusive).
            - "baseline_docs" (int): count of documents in the baseline (published <= BASELINE_CUTOFF).
            - "cumulative_docs" (int): count of documents published <= cutoff.
            - For each metric in METRICS, three keys with rounded values:
                - "no_reindex_<metric>"
                - "append_<metric>"
                - "global_<metric>"
    
    Raises:
        RuntimeError: if the dataset bundle contains no qrels for the configured snapshot.
    """
    config = clone_for_train_eval(load_config(str(CONFIG_PATH)))
    bundle = load_dataset_bundle(config.dataset, SNAPSHOT_ID)

    if bundle.qrels is None:
        raise RuntimeError("No qrels found for snapshot-1-train.")

    run = read_trec_run(run_path)

    # Fixed qrels: all relevant docs published within the full window
    window_docs = _doc_ids_by_cutoff(bundle, WINDOW_END)
    full_qrels: dict[str, dict[str, int]] = {
        qid: {d: r for d, r in docrels.items() if d in window_docs}
        for qid, docrels in bundle.qrels.items()
    }
    full_qrels = {qid: dr for qid, dr in full_qrels.items() if dr}
    allowed_qids = set(full_qrels.keys())

    # Baseline doc set for scenario 1 (no reindex)
    baseline_docs = _doc_ids_by_cutoff(bundle, BASELINE_CUTOFF)
    print(f"Baseline docs (publishedDate < {WINDOW_START.date()}): {len(baseline_docs):,}")
    print(f"Full window docs (publishedDate <= {WINDOW_END.date()}): {len(window_docs):,}")
    print(f"Queries with qrels in full window: {len(allowed_qids)}")
    print()

    results = []
    cutoff = WINDOW_START + timedelta(days=step_days - 1)
    while cutoff <= WINDOW_END:
        cumulative_docs = _doc_ids_by_cutoff(bundle, cutoff)

        # Scenario 1: no reindex — fixed baseline index
        run1 = _filter_run(run, baseline_docs, allowed_qids)
        agg1 = _eval(full_qrels, run1)

        # Scenario 2: append reindex — index grows to cutoff
        run2 = _filter_run(run, cumulative_docs, allowed_qids)
        agg2 = _eval(full_qrels, run2)

        # Scenario 3: global reindex — same as append for static data
        agg3 = agg2

        results.append({
            "cutoff_date": cutoff.strftime("%Y-%m-%d"),
            "days_since_start": (cutoff - WINDOW_START).days + 1,
            "baseline_docs": len(baseline_docs),
            "cumulative_docs": len(cumulative_docs),
            **{f"no_reindex_{m}": round(agg1.get(m, 0.0), 4) for m in METRICS},
            **{f"append_{m}": round(agg2.get(m, 0.0), 4) for m in METRICS},
            **{f"global_{m}": round(agg3.get(m, 0.0), 4) for m in METRICS},
        })
        cutoff += timedelta(days=step_days)

    return results


def write_outputs(results: list[dict], output_dir: Path) -> None:
    """
    Write the provided results to CSV and JSON files inside the given output directory.
    
    Creates the directory if it does not exist, writes:
    - scenario_comparison.csv: a CSV using the first result's keys as column headers and all rows from `results`.
    - scenario_comparison.json: pretty-printed JSON with two-space indentation.
    
    Parameters:
        results (list[dict]): Sequence of per-cutoff result records (each dict represents one row).
        output_dir (Path): Directory where `scenario_comparison.csv` and `scenario_comparison.json` will be written.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / "scenario_comparison.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    json_path = output_dir / "scenario_comparison.json"
    json_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Data written: {csv_path.name}, {json_path.name}")


def plot_results(results: list[dict], output_dir: Path) -> None:
    """
    Create and save a two-row plot showing nDCG@10 over cutoff dates for three reindexing scenarios and the cumulative document count.
    
    Parameters:
        results (list[dict]): Sequence of per-cutoff result dictionaries. Each dict must contain the keys
            "cutoff_date", "no_reindex_ndcg_cut_10", "append_ndcg_cut_10", "global_ndcg_cut_10", and "cumulative_docs".
        output_dir (Path): Directory where the PNG plot "scenario_comparison_ndcg10.png" will be written.
    
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.ticker as mticker
    except ImportError:
        print("matplotlib not available — skipping plot")
        return

    dates = [r["cutoff_date"] for r in results]
    ndcg_no = [r["no_reindex_ndcg_cut_10"] for r in results]
    ndcg_ap = [r["append_ndcg_cut_10"] for r in results]
    ndcg_gl = [r["global_ndcg_cut_10"] for r in results]
    docs_cum = [r["cumulative_docs"] / 1_000 for r in results]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True,
                                    gridspec_kw={"height_ratios": [3, 1]})

    ax1.plot(dates, ndcg_no, "r-o", linewidth=2, markersize=5, label="No Reindex (fixed baseline)")
    ax1.plot(dates, ndcg_ap, "g-s", linewidth=2, markersize=5, label="Append Reindex (incremental)")
    ax1.plot(dates, ndcg_gl, "b--^", linewidth=1.5, markersize=4, alpha=0.6, label="Global Reindex (full rebuild)")
    ax1.set_ylabel("nDCG@10", fontsize=12)
    ax1.set_title("BM25 Fulltext — nDCG@10 Under Three Reindex Strategies\n"
                  f"Snapshot-1 ({WINDOW_START.date()} → {WINDOW_END.date()}) | date_field={DATE_FIELD}",
                  fontsize=13)
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3)
    ax1.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.4f"))

    ax2.fill_between(dates, docs_cum, alpha=0.4, color="steelblue")
    ax2.plot(dates, docs_cum, "steelblue", linewidth=1.5)
    ax2.set_ylabel("Cumulative Docs (k)", fontsize=10)
    ax2.set_xlabel("Cutoff Date", fontsize=12)
    ax2.grid(True, alpha=0.3)

    tick_step = max(1, len(dates) // 10)
    tick_positions = list(range(0, len(dates), tick_step))
    ax1.set_xticks([dates[i] for i in tick_positions])
    ax2.set_xticks([dates[i] for i in tick_positions])
    plt.setp(ax2.get_xticklabels(), rotation=30, ha="right", fontsize=9)

    plt.tight_layout()
    plot_path = output_dir / "scenario_comparison_ndcg10.png"
    fig.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Plot saved: {plot_path}")


def main() -> None:
    """
    Run the three-scenario reindex comparison as a command-line entry point.
    
    Parses CLI arguments for a TREC run file, step size in days, and output directory; validates the run file exists (exits with status 1 if missing); executes the cutoff-by-cutoff comparison, prints a tabular nDCG@10 summary to stdout, writes CSV/JSON results to the output directory, and attempts to generate and save an nDCG@10 plot.
    """
    parser = argparse.ArgumentParser(description="Three-scenario reindex comparison.")
    parser.add_argument(
        "--run",
        default=str(ROOT / "outputs" / "custom_lexical_fulltext" / "snapshot-1-train" / "run.txt"),
    )
    parser.add_argument("--step-days", type=int, default=7)
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "adaptive_monitor" / "outputs" / "scenario_comparison"),
    )
    args = parser.parse_args()

    run_path = Path(args.run)
    if not run_path.exists():
        print(f"ERROR: run file not found: {run_path}")
        sys.exit(1)

    print(f"Running scenario comparison (step={args.step_days}d) ...")
    results = run_comparison(run_path, step_days=args.step_days)

    print(f"\n{'Cutoff':12} {'NoDocs':>10} {'CumDocs':>10} {'No Reindex':>12} {'Append':>10} {'Global':>10}")
    print("-" * 72)
    for r in results:
        print(
            f"{r['cutoff_date']:12} {r['baseline_docs']:>10,} {r['cumulative_docs']:>10,} "
            f"{r['no_reindex_ndcg_cut_10']:>12.4f} {r['append_ndcg_cut_10']:>10.4f} "
            f"{r['global_ndcg_cut_10']:>10.4f}"
        )

    output_dir = Path(args.output_dir)
    write_outputs(results, output_dir)
    plot_results(results, output_dir)


if __name__ == "__main__":
    main()
