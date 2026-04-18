"""Build BM25 index on publishedDate <= 2025-03-31, then evaluate daily for April-May.

Step 1: Index docs with publishedDate <= MARCH_CUTOFF → march_run.txt
Step 2: For each day in April 1 - May 31, evaluate the fixed March run against
        qrels filtered to publishedDate <= cutoff (growing relevant set).

This correctly simulates "no reindex": the system deployed at end of March
cannot retrieve April-May papers, so nDCG@10 degrades as new relevant docs appear.

Usage:
    JAVA_HOME=... python adaptive_monitor/march_baseline_eval.py
    JAVA_HOME=... python adaptive_monitor/march_baseline_eval.py --step-days 1
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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from adaptive_monitor.incremental_reindex import iter_incremental_text_records  # noqa: E402
from longeval_sci.baselines.runner import (  # noqa: E402
    _ensure_pyterrier_started,
    clone_for_train_eval,
)
from longeval_sci.config import load_config  # noqa: E402
from longeval_sci.evaluation.pytrec_eval_wrapper import evaluate_run_dict  # noqa: E402
from longeval_sci.io.dataset import load_dataset_bundle  # noqa: E402
from longeval_sci.io.dataset import SearchResult  # noqa: E402
from longeval_sci.io.trec import read_trec_run, write_trec_run  # noqa: E402

METRICS = ["ndcg_cut_10", "ndcg_cut_1000", "map", "recall_100", "recall_1000"]
CONFIG_PATH = ROOT / "configs" / "custom_lexical_fulltext.yaml"
SNAPSHOT_ID = "snapshot-1"
DATE_FIELD = "publishedDate"

MARCH_CUTOFF = datetime(2025, 3, 31, 23, 59, 59, tzinfo=UTC)  # index frozen here
APRIL_START = datetime(2025, 4, 1, tzinfo=UTC)
WINDOW_END = datetime(2025, 5, 31, 23, 59, 59, tzinfo=UTC)
EPOCH = datetime(1900, 1, 1, tzinfo=UTC)  # "start_after" sentinel for all historical docs

INDEX_DIR = ROOT / "indexes" / "snapshot-1" / "full_text" / "march_baseline_pyterrier"
RUN_PATH = ROOT / "adaptive_monitor" / "outputs" / "march_baseline" / "run_march.txt"
OUTPUT_DIR = ROOT / "adaptive_monitor" / "outputs" / "march_baseline"


def _parse_dt(value: object) -> datetime | None:
    """
    Parse a value into a timezone-aware UTC datetime when possible.
    
    Parameters:
        value (object): An ISO-8601 datetime string (or any object convertible to string). A trailing "Z" is treated as UTC. Falsy values (None, empty string) are accepted.
    
    Returns:
        datetime | None: A timezone-aware `datetime` in UTC if parsing succeeds, otherwise `None`.
    """
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except ValueError:
        return None


def build_march_run(config, bundle, memory_mb: int | None = None) -> None:
    """
    Builds a PyTerrier index containing documents published on or before the March cutoff and writes a BM25 TREC run based on that index.
    
    If the index directory already exists (data.properties present) the function skips indexing and reuses the existing index. The function tokenizes the dataset queries, runs BM25 retrieval (up to 1000 results per query), converts results into TREC-format SearchResult entries, and writes the run file to the configured run path.
    
    Parameters:
        config: Configuration object that contains dataset identifiers and any settings required to iterate text records.
        bundle: Dataset bundle providing `queries` (used as retrieval topics) and other dataset metadata.
        memory_mb (int | None): Optional JVM memory (in megabytes) to pass when ensuring PyTerrier is started; if `None`, the default PyTerrier memory settings are used.
    """
    RUN_PATH.parent.mkdir(parents=True, exist_ok=True)

    pt = _ensure_pyterrier_started(memory_mb)
    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    if not (INDEX_DIR / "data.properties").exists():
        print(f"Building index (publishedDate <= {MARCH_CUTOFF.date()}) ...")
        indexer = pt.IterDictIndexer(
            str(INDEX_DIR.resolve()),
            overwrite=True,
            meta={"docno": 100, "text": 20480},
        )
        counter = {"n": 0}

        def filtered_records():
            """
            Yield text records from the dataset that have a publication date on or before the March cutoff.
            
            Yields:
                Records from the dataset iterator produced by `iter_incremental_text_records`, limited to documents with `publishedDate <= MARCH_CUTOFF`. Prints a progress message every 50,000 yielded records.
            """
            for rec in iter_incremental_text_records(
                config.dataset,
                SNAPSHOT_ID,
                "full_text",
                date_field=DATE_FIELD,
                start_after=EPOCH,
                end_at=MARCH_CUTOFF,
            ):
                counter["n"] += 1
                if counter["n"] % 50_000 == 0:
                    print(f"  Indexed {counter['n']:,} docs ...")
                yield rec

        indexer.index(filtered_records())
        print(f"  Index built: {counter['n']:,} docs")
    else:
        print(f"Index already exists at {INDEX_DIR}")

    print("Running BM25 retrieval ...")
    index = pt.IndexFactory.of(str(INDEX_DIR.resolve()))
    topics = pd.DataFrame([{"qid": q.query_id, "query": q.text} for q in bundle.queries])
    tokeniser = pt.java.autoclass("org.terrier.indexing.tokenisation.Tokeniser").getTokeniser()
    topics["query"] = topics["query"].apply(lambda v: " ".join(tokeniser.getTokens(v)))
    run_frame = pt.terrier.Retriever(index, wmodel="BM25", num_results=1000)(topics)

    results = [
        SearchResult(
            query_id=str(row["qid"]),
            doc_id=str(row["docno"]),
            score=float(row["score"]),
            rank=int(row["rank"]) + 1,
            run_name="bm25_march_baseline",
        )
        for _, row in run_frame.iterrows()
    ]
    write_trec_run(results, RUN_PATH)
    print(f"  Run saved: {RUN_PATH} ({len(results):,} rows)")


def _doc_ids_by_cutoff(bundle, cutoff: datetime) -> set[str]:
    """
    Return the set of document IDs whose `publishedDate` is parseable and less than or equal to the given cutoff.
    
    Parameters:
        bundle: Dataset bundle containing documents accessible via `bundle.documents`; each document must expose `doc_id` and `metadata`.
        cutoff (datetime): Cutoff datetime (compared in UTC) inclusive.
    
    Returns:
        A set of document ID strings for documents whose `publishedDate` parses successfully and is <= `cutoff`. Documents with missing or unparsable `publishedDate` values are excluded.
    """
    return {
        doc.doc_id
        for doc in bundle.documents
        if (dt := _parse_dt(doc.metadata.get(DATE_FIELD))) is not None and dt <= cutoff
    }


def evaluate_april_may(run: dict, bundle, step_days: int) -> list[dict]:
    """
    Evaluate a fixed March-only retrieval run against qrels that grow over time from April 1 to May 31.
    
    For each cutoff date (starting at APRIL_START + step_days - 1 and advancing by step_days until WINDOW_END) this function:
    - Restricts the supplied `run` to documents published on or before MARCH_CUTOFF.
    - Builds qrels containing only relevant documents whose `publishedDate` is on or before the current cutoff.
    - Evaluates the fixed March run against those cutoff-filtered qrels using the global METRICS.
    - Records counts (March doc count, cumulative doc count, new docs since March, queries with qrels) and the aggregated metrics (rounded to 4 decimals).
    
    Parameters:
        run (dict): Mapping from query id to a mapping of doc id -> score representing a retrieval run.
        bundle: Dataset bundle providing `.qrels` and document metadata used to determine document publication dates.
        step_days (int): Number of days between successive cutoffs.
    
    Returns:
        list[dict]: Ordered list of per-cutoff result dictionaries with keys:
            - "cutoff_date" (str): cutoff in "YYYY-MM-DD" format,
            - "march_docs" (int): number of documents available at MARCH_CUTOFF,
            - "cumulative_docs" (int): number of documents available at the cutoff,
            - "new_docs_since_march" (int): non-negative count of documents added since March,
            - "queries_with_qrels" (int): number of queries that have at least one relevant doc at the cutoff,
            - one entry per metric from METRICS with float values rounded to 4 decimals.
    """
    # Fixed run: only March-and-before docs
    march_docs = _doc_ids_by_cutoff(bundle, MARCH_CUTOFF)
    march_run = {
        qid: {d: s for d, s in docs.items() if d in march_docs}
        for qid, docs in run.items()
    }

    results = []
    cutoff = APRIL_START + timedelta(days=step_days - 1)
    while cutoff <= WINDOW_END:
        cutoff_docs = _doc_ids_by_cutoff(bundle, cutoff)
        # Qrels: relevant docs published up to this cutoff
        qrels_at_cutoff: dict[str, dict[str, int]] = {}
        for qid, docrels in bundle.qrels.items():
            kept = {d: r for d, r in docrels.items() if d in cutoff_docs}
            if kept:
                qrels_at_cutoff[qid] = kept

        if qrels_at_cutoff:
            agg, _ = evaluate_run_dict(qrels_at_cutoff, march_run, METRICS)
        else:
            agg = {m: 0.0 for m in METRICS}

        new_docs_this_step = len(cutoff_docs) - len(march_docs)
        results.append({
            "cutoff_date": cutoff.strftime("%Y-%m-%d"),
            "march_docs": len(march_docs),
            "cumulative_docs": len(cutoff_docs),
            "new_docs_since_march": max(new_docs_this_step, 0),
            "queries_with_qrels": len(qrels_at_cutoff),
            **{m: round(agg.get(m, 0.0), 4) for m in METRICS},
        })
        cutoff += timedelta(days=step_days)

    return results


def write_and_plot(results: list[dict], output_dir: Path) -> None:
    """
    Write evaluation results to CSV and JSON and generate a summary PNG plot.
    
    Parameters:
        results (list[dict]): Sequence of per-cutoff result dictionaries. Each dictionary must include the keys
            'cutoff_date' (date or datetime), 'ndcg_cut_10' (float), 'recall_1000' (float), and
            'new_docs_since_march' (int or float). All other keys will be written as additional CSV/JSON fields.
        output_dir (Path): Directory where outputs will be written. The function creates this directory if it
            does not exist.
    
    Behavior:
        - Writes march_baseline_daily_eval.csv and march_baseline_daily_eval.json into output_dir using the
          fields from the first result as CSV columns.
        - Attempts to generate march_baseline_april_may_eval.png plotting nDCG@10, Recall@1000, and new-doc
          volume over the cutoffs; if matplotlib is not available, plotting is skipped.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / "march_baseline_daily_eval.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    json_path = output_dir / "march_baseline_daily_eval.json"
    json_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Data: {csv_path.name}, {json_path.name}")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.ticker as mticker
    except ImportError:
        print("matplotlib not available — skipping plot")
        return

    dates = [r["cutoff_date"] for r in results]
    ndcg = [r["ndcg_cut_10"] for r in results]
    recall = [r["recall_1000"] for r in results]
    new_docs = [r["new_docs_since_march"] / 1_000 for r in results]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True,
                                    gridspec_kw={"height_ratios": [3, 1]})

    color_ndcg = "#d62728"
    color_rec = "#1f77b4"
    ax1.plot(dates, ndcg, "-o", color=color_ndcg, linewidth=2, markersize=4, label="nDCG@10")
    ax1_r = ax1.twinx()
    ax1_r.plot(dates, recall, "--s", color=color_rec, linewidth=1.5, markersize=4, alpha=0.8, label="Recall@1000")
    ax1_r.set_ylabel("Recall@1000", fontsize=11, color=color_rec)
    ax1_r.tick_params(axis="y", labelcolor=color_rec)

    ax1.set_ylabel("nDCG@10", fontsize=11, color=color_ndcg)
    ax1.tick_params(axis="y", labelcolor=color_ndcg)
    ax1.set_title(
        f"BM25 March Baseline (No Reindex) — Daily Eval Apr–May 2025\n"
        f"Index frozen at {MARCH_CUTOFF.date()} | date_field={DATE_FIELD}",
        fontsize=13,
    )
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax1_r.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, fontsize=10)
    ax1.grid(True, alpha=0.3)
    ax1.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.4f"))

    ax2.fill_between(dates, new_docs, alpha=0.4, color="orange")
    ax2.plot(dates, new_docs, color="orange", linewidth=1.5)
    ax2.set_ylabel("New Docs Since\nMarch (k)", fontsize=10)
    ax2.set_xlabel("Cutoff Date", fontsize=12)
    ax2.grid(True, alpha=0.3)

    tick_step = max(1, len(dates) // 10)
    ticks = [dates[i] for i in range(0, len(dates), tick_step)]
    ax1.set_xticks(ticks)
    ax2.set_xticks(ticks)
    plt.setp(ax2.get_xticklabels(), rotation=30, ha="right", fontsize=9)

    plt.tight_layout()
    plot_path = output_dir / "march_baseline_april_may_eval.png"
    fig.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Plot saved: {plot_path}")


def main() -> None:
    """
    Run the March-baseline build/evaluation pipeline that evaluates a fixed BM25 run over April–May.
    
    Parses CLI arguments, ensures a March-only BM25 run exists (building it unless skipped), evaluates that fixed run across expanding daily cutoffs from 2025-04-01 to 2025-05-31, prints a per-cutoff summary table, and writes CSV/JSON outputs and an optional plot to the configured output directory.
    
    CLI options:
        --step-days    Number of days between evaluation cutoffs (default: 7).
        --skip-build   If provided, reuse an existing run file instead of rebuilding the index/run.
        --memory-mb    Optional memory limit (MB) passed to the PyTerrier starter.
    
    Side effects:
        - May create an index and write a TREC run file.
        - Writes evaluation CSV and JSON and, if matplotlib is available, a PNG plot to the output directory.
    """
    parser = argparse.ArgumentParser(description="March baseline BM25 eval over April-May.")
    parser.add_argument("--step-days", type=int, default=7)
    parser.add_argument("--skip-build", action="store_true", help="Skip index/run build if run already exists.")
    parser.add_argument("--memory-mb", type=int, default=None)
    args = parser.parse_args()

    config = clone_for_train_eval(load_config(str(CONFIG_PATH)))
    bundle = load_dataset_bundle(config.dataset, SNAPSHOT_ID)

    if not args.skip_build or not RUN_PATH.exists():
        build_march_run(config, bundle, memory_mb=args.memory_mb)
    else:
        print(f"Skipping build — using existing run: {RUN_PATH}")

    print(f"\nEvaluating April-May with step={args.step_days}d ...")
    run = read_trec_run(RUN_PATH)
    results = evaluate_april_may(run, bundle, step_days=args.step_days)

    print(f"\n{'Cutoff':12} {'MarchDocs':>10} {'CumDocs':>10} {'NewDocs':>9} {'nDCG@10':>9} {'MAP':>7} {'R@1000':>8}")
    print("-" * 72)
    for r in results:
        print(
            f"{r['cutoff_date']:12} {r['march_docs']:>10,} {r['cumulative_docs']:>10,} "
            f"{r['new_docs_since_march']:>9,} {r['ndcg_cut_10']:>9.4f} "
            f"{r['map']:>7.4f} {r['recall_1000']:>8.4f}"
        )

    write_and_plot(results, OUTPUT_DIR)


if __name__ == "__main__":
    main()
