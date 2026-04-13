"""Build pivot-relative temporal change metrics from cumulative monthly split results."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


TRANSITIONS = [
    ("march_only", "march_april"),
    ("march_only", "march_april_may"),
    ("march_april", "march_april_may"),
]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_json(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(rows, handle, indent=2, sort_keys=True)


def _write_markdown(rows: list[dict[str, object]], metric: str, pivot: str, path: Path) -> None:
    lines = [
        "# Temporal Change Report",
        "",
        f"Primary score metric: `{metric}`",
        f"Pivot model: `{pivot}`",
        "",
        "Definitions:",
        "- `ARP`: score at the later split in the transition.",
        "- `MARP`: mean score across the earlier and later splits.",
        "- `RI`: `(earlier - later) / earlier`; lower is more robust, negative means improvement.",
        "- `DRI`: `RI(system) - RI(pivot)`.",
        "- `ER`: `RI(system) / RI(pivot)` with a small denominator floor.",
        "",
        "| Model | Transition | Earlier | Later | ARP | MARP | RI | DRI | ER |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            "| {model} | {transition} | {earlier_score:.4f} | {later_score:.4f} | {ARP:.4f} | {MARP:.4f} | {RI:.4f} | {DRI:.4f} | {ER:.4f} |".format(
                **{
                    **row,
                    "earlier_score": float(row["earlier_score"]),
                    "later_score": float(row["later_score"]),
                    "ARP": float(row["ARP"]),
                    "MARP": float(row["MARP"]),
                    "RI": float(row["RI"]),
                    "DRI": float(row["DRI"]),
                    "ER": float(row["ER"]),
                }
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _relative_improvement(earlier: float, later: float) -> float:
    if abs(earlier) < 1e-12:
        return 0.0
    return (earlier - later) / earlier


def main() -> None:
    parser = argparse.ArgumentParser(description="Build temporal change metrics from monthly split results.")
    parser.add_argument(
        "--input-csv",
        default="outputs/reports/monthly_split/_summary/monthly_comparison.csv",
        help="Monthly comparison CSV produced by build_monthly_split_summary.py",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs/reports/monthly_split/_summary/temporal_change",
        help="Directory for temporal change outputs.",
    )
    parser.add_argument(
        "--metric",
        default="ndcg_cut_10",
        choices=["ndcg_cut_10", "ndcg_cut_1000", "map", "recall_100", "recall_1000"],
        help="Primary score metric used for ARP/MARP/RI/DRI/ER.",
    )
    parser.add_argument(
        "--pivot",
        default="official_pyterrier_dctr",
        help="Pivot model name from monthly_comparison.csv",
    )
    parser.add_argument(
        "--epsilon",
        type=float,
        default=1e-9,
        help="Denominator floor for ER when the pivot RI is near zero.",
    )
    args = parser.parse_args()

    rows = _read_csv(Path(args.input_csv))
    lookup: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        lookup[(row["model"], row["split_name"])] = row

    output_rows: list[dict[str, object]] = []
    for earlier_split, later_split in TRANSITIONS:
        pivot_earlier = lookup.get((args.pivot, earlier_split))
        pivot_later = lookup.get((args.pivot, later_split))
        if pivot_earlier is None or pivot_later is None:
            raise SystemExit(f"Missing pivot rows for transition {earlier_split} -> {later_split}")

        pivot_ri = _relative_improvement(float(pivot_earlier[args.metric]), float(pivot_later[args.metric]))

        models = sorted({row["model"] for row in rows})
        for model in models:
            earlier = lookup.get((model, earlier_split))
            later = lookup.get((model, later_split))
            if earlier is None or later is None:
                continue
            earlier_score = float(earlier[args.metric])
            later_score = float(later[args.metric])
            ri = _relative_improvement(earlier_score, later_score)
            dri = ri - pivot_ri
            er = ri / (pivot_ri if abs(pivot_ri) >= args.epsilon else (args.epsilon if pivot_ri >= 0 else -args.epsilon))
            output_rows.append(
                {
                    "model": model,
                    "pivot": args.pivot,
                    "metric": args.metric,
                    "transition": f"{earlier_split}->{later_split}",
                    "earlier_split": earlier_split,
                    "later_split": later_split,
                    "earlier_score": earlier_score,
                    "later_score": later_score,
                    "ARP": later_score,
                    "MARP": (earlier_score + later_score) / 2.0,
                    "RI": ri,
                    "DRI": dri,
                    "ER": er,
                }
            )

    output_rows.sort(key=lambda row: (str(row["transition"]), float(row["DRI"]), str(row["model"])))

    output_dir = Path(args.output_dir)
    _write_csv(output_rows, output_dir / "temporal_change.csv")
    _write_json(output_rows, output_dir / "temporal_change.json")
    _write_markdown(output_rows, args.metric, args.pivot, output_dir / "temporal_change.md")

    print(f"csv: {output_dir / 'temporal_change.csv'}")
    print(f"json: {output_dir / 'temporal_change.json'}")
    print(f"markdown: {output_dir / 'temporal_change.md'}")


if __name__ == "__main__":
    main()
