# Snapshot-1 Train Comparison

This report uses the provided `snapshot-1` **train queries** and evaluates the same run files against two qrel variants.

Qrel variants:
- `raw`: every clicked document is marked relevant with label `1`.
- `dctr`: pseudo relevance labels derived from Document Click Through Rate and treated as graded relevance for nDCG.
- `MAP` and `Recall` use the same evaluator but effectively treat all relevance > 0 as relevant.

## DCTR Results

| Method | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | ---: | ---: | ---: | ---: | ---: |
| official_pyterrier | 0.2922 | 0.4564 | 0.2573 | 0.6836 | 0.8581 |
| official_pyterrier_dense | 0.2820 | 0.4483 | 0.2378 | 0.6390 | 0.8613 |
| custom_lexical_fulltext | 0.3302 | 0.5077 | 0.2853 | 0.7394 | 0.9245 |
| custom_title_abstract_rm3 | 0.2781 | 0.4510 | 0.2402 | 0.6559 | 0.8701 |
| custom_title_abstract_rerank | 0.3222 | 0.4821 | 0.2777 | 0.6952 | 0.8581 |

## Raw Results

| Method | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | ---: | ---: | ---: | ---: | ---: |
| official_pyterrier | 0.3310 | 0.5034 | 0.2658 | 0.6831 | 0.8561 |
| official_pyterrier_dense | 0.3106 | 0.4875 | 0.2402 | 0.6379 | 0.8555 |
| custom_lexical_fulltext | 0.3637 | 0.5504 | 0.2899 | 0.7324 | 0.9205 |
| custom_title_abstract_rm3 | 0.3074 | 0.4934 | 0.2469 | 0.6534 | 0.8688 |
| custom_title_abstract_rerank | 0.3373 | 0.5152 | 0.2750 | 0.6836 | 0.8561 |

## Notes

- `official_pyterrier` and `official_pyterrier_dense` are the downloaded official BM25 and Qwen reference runs.
- `custom_lexical_fulltext` is the full-text BM25 overlay.
- `custom_title_abstract_rm3` applies RM3 query expansion on top of the shared title+abstract lexical index.
- `custom_title_abstract_rerank` applies cross-encoder reranking on top of title+abstract lexical candidates.
