# Snapshot-1 Train Comparison

This report uses the provided `snapshot-1` **train queries** and evaluates the same run files against two qrel variants.

Qrel variants:
- `raw`: every clicked document is marked relevant with label `1`. In your local file, all labels are binary positives.
- `dctr`: pseudo relevance labels derived from Document Click Through Rate. In your local file, labels are graded (`0`, `1`, `2`).
- The retrieval metrics are computed the same way in both cases; only the qrel labels change.
- For `nDCG`, graded labels matter directly, so `dctr` can reward ranking a stronger pseudo-relevant document above a weaker one.
- For `MAP` and `Recall`, any document with relevance > 0 is treated as relevant by the evaluator, so the main difference is in which documents are labeled relevant at all.

## DCTR Results

| Method | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | ---: | ---: | ---: | ---: | ---: |
| official_pyterrier | 0.2922 | 0.4564 | 0.2573 | 0.6836 | 0.8581 |
| reference_qwen3 | 0.2820 | 0.4483 | 0.2378 | 0.6390 | 0.8613 |
| custom_lexical_fulltext | 0.3302 | 0.5077 | 0.2853 | 0.7394 | 0.9245 |
| custom_dense_rerank | 0.1284 | 0.1686 | 0.0853 | 0.2925 | 0.3106 |
| custom_hybrid_union_rerank | 0.1371 | 0.3580 | 0.1245 | 0.5316 | 0.9388 |

## Raw Results

| Method | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | ---: | ---: | ---: | ---: | ---: |
| official_pyterrier | 0.3310 | 0.5034 | 0.2658 | 0.6831 | 0.8561 |
| reference_qwen3 | 0.3106 | 0.4875 | 0.2402 | 0.6379 | 0.8555 |
| custom_lexical_fulltext | 0.3637 | 0.5504 | 0.2899 | 0.7324 | 0.9205 |
| custom_dense_rerank | 0.1457 | 0.1892 | 0.0845 | 0.2837 | 0.3044 |
| custom_hybrid_union_rerank | 0.1504 | 0.3947 | 0.1288 | 0.5454 | 0.9359 |

## Notes

- `official_pyterrier` is the official BM25 baseline. It matches the downloaded BM25 reference on DCTR exactly, so we use the local run as the canonical BM25 result here.
- `reference_qwen3` is the downloaded official dense baseline output using `Qwen3-Embedding-4B` from the organizer baseline package.
- `custom_lexical_fulltext` now runs against the local fulltext cache and is the strongest model on this train split under both qrel variants.
- `custom_dense_rerank` and `custom_hybrid_union_rerank` currently underperform the lexical baselines on this split, so they are good candidates for further debugging or retuning.