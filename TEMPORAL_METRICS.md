# Temporal Metrics on Simulated Month Growth

This note explains how the repo maps LongEval-style change-oriented metrics onto our **simulated cumulative month splits** inside `snapshot-1`.

Reference framing:

- LongEval 2025 overview paper, Sections 5.2 and 5.3: https://arxiv.org/html/2509.17469v1

## Where This Fits in Our Evaluation Stack

We now use three evaluation layers:

1. whole-train evaluation
   - full `snapshot-1 train` performance for method comparison and model selection
2. monthly split evaluation
   - cumulative within-snapshot growth from `march_only` to `march_april_may`
3. temporal change evaluation
   - RI / DRI / ER / ARP / MARP derived from the monthly split results

So temporal change metrics are the **top layer** of the current evaluation workflow. They help us interpret how systems change, but they should always be read alongside the underlying train and monthly metrics.

## Our Three Simulated States

For `snapshot-1`, the current cumulative month evaluation uses:

1. `march_only`
2. `march_april`
3. `march_april_may`

These are **not** official benchmark snapshots. They are an internal simulation of corpus growth inside the first official development snapshot.

That means these metrics should be interpreted as:

- a development-time robustness analysis
- not a direct substitute for the official longitudinal benchmark

## Pivot System

Like the LongEval overview, we use a **pivot system** to separate:

- raw absolute effectiveness
- system effect relative to a stable baseline

Recommended pivot:

- `official_pyterrier`

Why:

- it is the sparse official lexical anchor
- it is simple and stable
- it matches the benchmark framing well

## Absolute Performance Metrics

These are already available from our whole-train and monthly reports:

- `nDCG@10`
- `nDCG@1000`
- `MAP`
- `Recall@100`
- `Recall@1000`

For temporal analysis, the simplest summary views are:

- the metric at each cumulative month stage
- the change between stages

## ARP and MARP

The LongEval paper describes:

- `ARP`: Average Retrieval Performance at the evolved snapshot
- `MARP`: Mean Average Retrieval Performance across the compared snapshots

In our simulated setup:

- choose one metric as the instantiation metric, usually `nDCG@10`
- treat the later month set as the evolved snapshot

Examples:

- short-term simulated growth:
  - from `march_only` to `march_april`
  - `ARP = nDCG@10(march_april)`
  - `MARP = mean(nDCG@10(march_only), nDCG@10(march_april))`

- longer simulated growth:
  - from `march_only` to `march_april_may`
  - `ARP = nDCG@10(march_april_may)`
  - `MARP = mean(nDCG@10(march_only), nDCG@10(march_april_may))`

## RI: Relative Improvement

The LongEval overview says RI measures how effectiveness changes over time, with values below zero indicating improving effectiveness. That implies a change-style measure where lower is more robust.

For our simulated month-growth setup, a practical implementation is:

```text
RI(system; A -> B) = (score(system, A) - score(system, B)) / score(system, A)
```

Where:

- `A` is the earlier stage
- `B` is the later stage
- `score` is usually `nDCG@10`

Interpretation:

- `RI < 0`: system improved from A to B
- `RI = 0`: unchanged
- `RI > 0`: system degraded

Examples:

- `RI(system; march_only -> march_april)`
- `RI(system; march_only -> march_april_may)`

## DRI: Delta Relative Improvement

The LongEval overview explains DRI as a **pivot-relative** change measure. The goal is to dampen changes caused by the evolving collection itself and emphasize the system's own effect relative to BM25.

For our simulated setup:

```text
DRI(system; A -> B, pivot) = RI(system; A -> B) - RI(pivot; A -> B)
```

Recommended pivot:

- `official_pyterrier`

Interpretation:

- `DRI < 0`: the system changed less badly than the pivot, or improved more than the pivot
- `DRI = 0`: same temporal behavior as the pivot
- `DRI > 0`: worse temporal behavior than the pivot

## ER: Effect Ratio

The paper groups ER with RI and DRI as another pivot-relative system-effect measure. A practical way to operationalize it in our setup is as a ratio of relative changes:

```text
ER(system; A -> B, pivot) = RI(system; A -> B) / RI(pivot; A -> B)
```

This needs a small epsilon safeguard if the pivot change is very close to zero.

Interpretation:

- `ER < 1`: the system is more robust than the pivot
- `ER = 1`: same change profile as the pivot
- `ER > 1`: less robust than the pivot

If the pivot RI is zero or nearly zero, ER becomes unstable. In that case:

- prefer DRI
- or report ER with a small denominator floor and document that choice

## Current Implementation

The repo now computes these metrics through:

```powershell
python scripts/build_temporal_change_report.py
```

It reads:

- `outputs/reports/monthly_split/_summary/monthly_comparison.csv`

and writes:

- `outputs/reports/monthly_split/_summary/temporal_change/temporal_change.csv`
- `outputs/reports/monthly_split/_summary/temporal_change/temporal_change.json`
- `outputs/reports/monthly_split/_summary/temporal_change/temporal_change.md`

for the current monthly comparison set using `official_pyterrier` as the pivot.

## Practical Reading Order

When comparing systems, the best order is:

1. read the whole-train report first
   - this tells us absolute effectiveness on `snapshot-1 train`
2. read the monthly split report second
   - this tells us how the same systems behave as the simulated corpus grows
3. read the temporal change report third
   - this tells us whether a system's change profile is better or worse than the BM25 pivot

That sequence keeps the interpretation grounded:

- full-train metrics answer "how good is it?"
- monthly metrics answer "how does it behave as the corpus grows?"
- temporal change metrics answer "is that behavior better or worse than the pivot system?"

## Important Interpretation Note

These metrics are **derived from our simulated cumulative month splits**, not from official LongEval future snapshots.

So they should be described as:

- internal temporal robustness proxies
- grounded in the LongEval metric philosophy
- useful for development and model selection

But they are **not** identical to the official benchmark's longitudinal evaluation over independently collected snapshots.
