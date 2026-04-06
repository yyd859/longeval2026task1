# AGENT.md

## Project context

This repository is for our participation in the **CLEF LongEval lab**, specifically:

- **LongEval 2026 – Task 1: LongEval-Sci**
- with future extension hooks for later time-aware and update-trigger experiments

For now, the immediate goal is to build **Run 1**, which is the **strong non-stupid retrieval baseline** for the scientific retrieval task.

This codebase is being built as research infrastructure, not just a one-off leaderboard script.

That means the repository should be designed to support:

1. **reproducible baselines**
2. **clean ablations**
3. **future temporal extensions**
4. **clear evaluation and reporting**
5. **easy handoff to additional runs later**

The initial deliverable is a strong retrieval and reranking stack that can serve as the control system for more advanced longitudinal methods.

---

## What this lab is about

The **LongEval** lab is about **longitudinal evaluation**: retrieval systems should not only work well on one static collection, but should also remain effective as the corpus evolves over time.

For **LongEval-Sci**, the benchmark focuses on scientific search over **multiple snapshots** of a scientific corpus. The main research question is not only:

- “Can we retrieve relevant scientific documents well?”

but also:

- “How does retrieval behave as the scientific collection changes?”
- “When do systems need updating?”
- “Can we build systems that are robust to temporal drift?”

Even though this repository is currently for **Run 1**, Codex should understand that this run is part of a larger 3-run research plan:

### Run 1
**Strong baseline retrieval system**
- lexical
- dense
- reranking
- hybrid candidate union

### Run 2
**Time-aware / resilience-oriented retrieval**
- temporal features
- query-type aware handling
- historical/variant-aware methods
- citation-aware priors

### Run 3
**Trigger / update policy system**
- decide when to retrain, refresh, or reuse
- balance compute cost and quality
- optimize update cadence vs retrieval performance

So the code should be modular enough that Run 2 and Run 3 can be added later without major rewrites.

---

## The current focus

**Do not implement Run 2 or Run 3 yet.**

The current focus is to build **Run 1** only.

Run 1 should answer this research need:

> What is the strongest plain retrieval system we can build for LongEval-Sci before adding explicit temporal reasoning?

This is important because later temporal improvements are only meaningful if the baseline is already strong.

We do **not** want a toy baseline.

We want a baseline that is competitive with:
- BM25 full-text baselines
- simple embedding baselines
- standard dense retrieval systems
- strong reranking pipelines

---

## What papers Codex should know about

Codex should treat the following papers/pages as the main references for architecture and benchmarking decisions.

---

## Primary benchmark references

### 1. LongEval 2026 task page
**Use this to understand the official task framing and constraints.**

Reference:
- https://clef-longeval.github.io/tasks/

What to learn from it:
- Task 1 is the scientific retrieval task for 2026
- the corpus is snapshot-based and evolves over time
- the task is longitudinal, not just static retrieval
- future runs may use citation data and time-aware evaluation ideas

Even though Run 1 is not explicitly time-aware yet, the dataset/evaluation code should be written in a way that supports multiple snapshots cleanly.

---

### 2. LongEval at CLEF 2025: Longitudinal Evaluation of IR Systems on Web and Scientific Data
**This is the most important overview paper for understanding the benchmark ecosystem.**

Reference:
- arXiv / overview paper: `LongEval at CLEF 2025: Longitudinal Evaluation of IR Systems on Web and Scientific Data`

Important:
- Read the **scientific retrieval task results**, not just the web task
- Pay attention to the benchmark philosophy:
  - raw retrieval quality matters
  - but robustness over time also matters
- This paper contains the tables showing how different systems performed

Codex should use this paper to understand:
- what types of runs were competitive in 2025
- why raw nDCG and temporal robustness are different objectives
- how the scientific task differs from the web task

### Important note for Codex
Be careful:
- in the **2025 overview**, the scientific retrieval task was **Task 2**
- in the **2026 setup**, the scientific retrieval task is **Task 1**

So when reading 2025 papers/tables, map **SciRetrieval 2025** to **Task 1 in 2026**.

---

## Primary modeling references for Run 1

### 3. AGH IR at LongEval 2025: Improving Scientific Information Retrieval with Dense Representations and Cross-Encoder Re-ranking
This is one of the most relevant implementation references for our current Run 1.

Codex should use this paper to guide:
- dense retrieval design
- title + abstract document representation
- reranking setup
- practical strong baselines for scientific retrieval

Main lessons from this paper:
- dense retrieval can be strong in scientific retrieval
- cross-encoder reranking is important
- title + abstract is a useful text representation
- candidate recall matters
- dense + reranking can outperform weaker lexical/hybrid setups

This paper is one of the best direct references for our initial pipeline.

---

### 4. OpenWebSearch at CLEF 2025: LongEval
This is useful conceptually, but mainly for later runs.

Codex should know it because:
- it shows historical query information can help
- it explores query-intent-aware and history-aware strategies
- it suggests that retrieval can benefit from prior relevance patterns

For Run 1, this is **not** the main implementation reference.
For Run 2 and Run 3, it becomes much more relevant.

So:
- keep the code extensible enough to support history-aware methods later
- but do not implement those methods now

---

### 5. CIR_cluster at LongEval 2025
This is mainly relevant for query clustering / temporal transfer ideas.

Again:
- useful for future architecture planning
- not a priority for Run 1 implementation

Codex should simply keep in mind that query clustering and variant reuse may later be added, so pipeline components should remain modular.

---

## Secondary papers for future runs

These are not required for Run 1 implementation, but Codex should know why the repository is being shaped a certain way.

### 6. TempRALM
Usefulness:
- conceptual basis for time-aware retrieval
- later relevant for Run 2

### 7. Query Performance Prediction / adaptive retrieval papers
Usefulness:
- conceptual basis for Run 3
- decide when to refresh or retrain

These do not need to be implemented now, but the repository should make later experimentation easy.

---

## Research framing for this repository

Codex should understand that this repository is part of a research agenda with the following hypothesis:

> Strong scientific retrieval in a longitudinal benchmark requires a high-quality static baseline first, before adding temporal adaptation and update policies.

Therefore, the code should prioritize:
- correctness
- reproducibility
- extensibility
- good experiment hygiene

This is **not** just a demo project.

---

## Immediate objective for Codex

Build **Run 1** infrastructure and initial experiments.

Run 1 should include:

1. **BM25 lexical retrieval**
2. **dense retrieval**
3. **cross-encoder reranking**
4. **hybrid candidate union + reranking**
5. **evaluation**
6. **ablation-friendly configs**

The result should let us compare:
- lexical vs dense
- dense vs dense+rerank
- lexical+dense union vs single-source candidate generation

---

## What Run 1 should prove

Run 1 should help answer these questions:

1. How competitive is tuned BM25 on this benchmark?
2. Can dense retrieval beat BM25 in scientific retrieval here?
3. How much does reranking help?
4. Does hybrid candidate union help recall before reranking?
5. Which text field representation works best:
   - title
   - abstract
   - title + abstract
   - full text
   - title + abstract + full text?

Run 1 is the baseline for all later claims.  
If Run 1 is weak, later temporal improvements are not meaningful.

---

## Non-goals for the current phase

Do **not** implement yet:

- temporal intent classification
- time-aware scoring
- historical query reuse
- query clustering transfer
- citation-graph propagation
- trigger/retraining policy
- adaptive update cadence
- agent workflows
- LLM query rewriting

These are future work for Run 2 and Run 3.

However, write the code so these can be added later.

---

## Architecture philosophy

The repository should be built like a small research platform.

### Design requirements
- modular
- easy to swap retrievers
- easy to swap rerankers
- easy to evaluate multiple runs
- easy to run ablations
- easy to add temporal features later

### Avoid
- hardcoded one-off scripts
- logic embedded only in notebooks
- brittle dataset assumptions
- monolithic code paths that make future runs hard to add

---

## Practical interpretation of the benchmark for coding

Even though Run 1 is “static”, the code should already support:

- multiple corpus snapshots
- choosing which snapshot to run on
- separate runs per snapshot
- separate outputs per snapshot
- per-query metrics and aggregate metrics

This is because later longitudinal analysis will need these cleanly.

So:
- snapshots should be explicit in config and paths
- outputs should carry snapshot IDs
- evaluation should be snapshot-aware

---

## Recommended project structure

Use a clean Python package layout like:

```text
longeval_sci/
├── AGENT.md
├── README.md
├── pyproject.toml
├── requirements.txt
├── configs/
│   ├── bm25_fulltext.yaml
│   ├── bm25_title_abstract.yaml
│   ├── dense_ta.yaml
│   ├── dense_ta_rerank.yaml
│   └── hybrid_union_rerank.yaml
├── data/
│   └── .gitkeep
├── outputs/
│   └── .gitkeep
├── scripts/
│   ├── build_bm25_index.py
│   ├── build_dense_index.py
│   ├── run_retrieval.py
│   ├── run_rerank.py
│   ├── evaluate_run.py
│   └── run_pipeline.py
├── src/
│   └── longeval_sci/
│       ├── __init__.py
│       ├── config.py
│       ├── io/
│       │   ├── dataset.py
│       │   ├── readers.py
│       │   └── trec.py
│       ├── preprocess/
│       │   ├── text.py
│       │   └── fields.py
│       ├── retrieval/
│       │   ├── bm25.py
│       │   ├── dense.py
│       │   ├── hybrid.py
│       │   └── faiss_utils.py
│       ├── rerank/
│       │   └── cross_encoder.py
│       ├── evaluation/
│       │   ├── metrics.py
│       │   └── pytrec_eval_wrapper.py
│       ├── pipeline/
│       │   └── runner.py
│       └── utils/
│           ├── logging.py
│           ├── seed.py
│           └── paths.py
└── tests/
    ├── test_dataset.py
    ├── test_bm25.py
    ├── test_dense.py
    ├── test_rerank.py
    └── test_pipeline_smoke.py

    