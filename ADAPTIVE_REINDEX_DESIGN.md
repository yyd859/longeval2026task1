# Adaptive Reindexing System Design

This document describes the design of a monitoring and adaptive reindexing pipeline
for the LongEval-Sci retrieval system.

The goal is to answer three practical questions:

1. How do we detect when the index has become stale without access to real-time qrels?
2. When and how should we trigger reindexing?
3. How do we evaluate the adaptive system end-to-end?

---

## Motivation

A static index degrades over time as new documents accumulate and the collection drifts
away from what the index was built on. LongEval-Sci directly evaluates this problem:
systems are scored across multiple snapshots, and temporal robustness is a first-class
evaluation criterion alongside raw effectiveness.

The adaptive reindexing system is designed to maintain retrieval effectiveness under
collection evolution, without full reindexing on every update cycle.

---

## Layer 1 — Monitoring Metrics

In a production setting there are no real-time qrels. Monitoring therefore relies on
**proxy signals** derived from the document collection and the retrieval system itself.

### Collection-Side Signals

| Metric | Definition | What it detects |
| --- | --- | --- |
| **Doc Staleness Rate** | Fraction of top-K results older than a threshold (e.g. 90 days) | Index not reflecting new content |
| **Index Coverage Gap** | New documents since last reindex / total indexed documents | How far the index has drifted from the live collection |
| **New Doc Velocity** | Rate of new document ingestion per day | How fast the collection is growing |
| **Temporal Gap** | Query timestamp minus mean publication date of top-K results | Whether retrieved results are falling behind the query time |

### Retrieval-Side Signals (No Labels Required)

| Metric | Definition |
| --- | --- |
| **Score Distribution Shift** | KL divergence between current retrieval score distribution and a baseline period |
| **Rank Stability** | Fraction of top-10 results that change for a fixed anchor query set between evaluation periods |
| **Retrieval Confidence Drop** | Moving average of the top-1 score falling below a baseline threshold |

### Implicit Feedback Signals (If Available)

- Click-through rate at rank k (CTR@k)
- Dwell time on retrieved results
- Query abandonment or bounce rate

These are optional and depend on the deployment environment. The proxy signals above
are sufficient for a no-label monitoring baseline.

---

## Layer 2 — Trigger Pipeline

The trigger pipeline continuously monitors proxy signals and decides whether and how
to reindex.

```
New documents ingested continuously
            ↓
    [Collection Monitor]
     Compute proxy metrics
     Compare against baseline period
            ↓
     [Drift Detector]
      Any metric exceeds threshold → open evaluation window
            ↓
     [Reindex Decision]
      Incremental append vs full rebuild
            ↓
     [Shadow Index]
      Build new index in isolation
            ↓
     [A/B Evaluation]
      Compare new and old index on anchor query set
            ↓
     [Promote or Rollback]
      Promote if new index is better, rollback otherwise
```

### Trigger Levels

Three alert levels control how aggressively reindexing is triggered.

**Level 1 — Soft alert (log only)**

```
Doc Staleness Rate > 15%
AND Index Coverage Gap > 5%
```

Indicates the index is drifting. Record and monitor but do not reindex yet.

**Level 2 — Incremental reindex**

```
Temporal Gap growth > 30 days
OR New Doc Velocity increases by more than 2x baseline
```

Append new documents to the existing index without a full rebuild.

**Level 3 — Full rebuild**

```
Rank Stability drops > 20% over 3 consecutive evaluation periods
```

Tear down and rebuild the index from scratch. This is expensive and should only fire
when incremental updates are no longer sufficient.

### Index-Type Considerations

Different index types have different incremental update costs.

| Index type | Incremental cost | Recommended trigger level |
| --- | --- | --- |
| BM25 (PyTerrier lexical) | Low — append is cheap | Level 2 |
| Dense (Qwen embedding) | High — embeddings must be recomputed | Level 3 only |
| RRF fusion | No index — reuses run files | Triggered by upstream index |

This means the BM25 branch can be refreshed frequently while the dense branch is
rebuilt only when strictly necessary.

---

## Layer 3 — Reindex Strategies

| Strategy | When to use | Cost |
| --- | --- | --- |
| **Incremental append** | New documents are few and collection changes slowly | Low |
| **Selective reindex** | A specific document category or time window has changed heavily | Medium |
| **Full rebuild** | Large-scale update, structural changes to the document schema, or sustained rank stability drop | High |

The default preference is incremental append. Full rebuild is the fallback when
incremental updates have accumulated enough drift that they no longer recover quality.

---

## Layer 4 — System Evaluation

Evaluating an adaptive reindexing system requires measuring effectiveness over time,
not at a single point. The evaluation target is not a single retrieval run but the
**trajectory of effectiveness across snapshots**.

### 4.1 Offline Simulation Using LongEval Monthly Splits

The LongEval monthly split reports provide an ideal simulation environment. Each
monthly split acts as a new snapshot, and new documents can be introduced incrementally
to simulate real collection growth.

```
Month:     M1    M2    M3    M4    M5
            ↓     ↓     ↓     ↓     ↓
Static:    eval  eval  eval  eval  eval   (index never updated)
Adaptive:  eval  [trigger → reindex]  eval  eval  eval
```

The comparison between the static and adaptive trajectories shows how much the
reindexing system recovers and maintains effectiveness over time.

### 4.2 Core Evaluation Metrics

These metrics extend the existing LongEval temporal metrics to cover the adaptive
system behavior.

| Metric | Definition | What it measures |
| --- | --- | --- |
| **Retention Index (RI)** | nDCG@10 on new snapshot / nDCG@10 on old snapshot | Whether effectiveness is maintained over time |
| **Recovery Rate** | Time (in periods) for nDCG@10 to return to pre-drift level after reindex | How quickly reindexing restores quality |
| **Reindex Cost-Benefit Ratio** | ΔnDCG@10 / reindex wall-clock time | Whether each reindex operation was worth the cost |
| **False Trigger Rate** | Fraction of reindex events where effectiveness had not actually dropped | Whether the trigger is too sensitive |
| **Miss Rate** | Fraction of true effectiveness drops that did not trigger reindexing | Whether the trigger is too conservative |

The False Trigger Rate and Miss Rate trade off against each other and can be plotted
as a ROC curve across different threshold settings.

### 4.3 Evaluation Pseudocode

```python
for month in monthly_splits:

    # Static system — never reindexes
    static_score = evaluate(static_index, month.queries, month.qrels)

    # Adaptive system — reindexes when drift is detected
    drift_detected = monitor.check(month.new_docs, month.queries)
    if drift_detected:
        adaptive_index.reindex(month.new_docs)
    adaptive_score = evaluate(adaptive_index, month.queries, month.qrels)

    log(month, static_score, adaptive_score, drift_detected)

# Final report
plot nDCG@10 over time: static vs adaptive
compute RI, Recovery Rate, Cost-Benefit Ratio
compute False Trigger Rate and Miss Rate at multiple thresholds
```

### 4.4 Ablation Axes

The following ablations isolate the contribution of individual design choices.

| Ablation | Question |
| --- | --- |
| Trigger threshold sweep | How does the False Trigger / Miss Rate trade-off change with threshold? |
| Incremental vs full rebuild | Does full rebuild recover more quality, and at what cost? |
| Reindex frequency | Weekly vs monthly vs event-driven — which minimizes effectiveness loss? |
| Proxy metric selection | Which proxy signal best predicts true effectiveness drop? |
| Dense vs lexical branch | Is rebuilding only the BM25 index sufficient in most cases? |

---

## Design Principles

- **Trigger signals must not require qrels.** All monitoring is based on proxy signals
  derivable from the document collection and retrieval outputs alone.
- **Evaluation uses real qrels.** The simulation study uses LongEval qrels to measure
  true effectiveness, separate from the monitoring layer.
- **Incremental by default, full rebuild as fallback.** Minimizing rebuild cost makes
  the system practical at scale.
- **Shadow indexing before promotion.** New indexes are evaluated against anchor queries
  before replacing the live index, preventing a bad reindex from degrading production quality.
- **LongEval monthly splits are the primary simulation testbed.** They provide a
  realistic multi-snapshot trajectory without requiring a separate data collection effort.
