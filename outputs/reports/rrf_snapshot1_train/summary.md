# Snapshot-1 Train RRF Fusion Comparison

| Method | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | ---: | ---: | ---: | ---: | ---: |
| official_pyterrier | 0.2922 | 0.4564 | 0.2573 | 0.6836 | 0.8581 |
| official_pyterrier_dense | 0.2820 | 0.4483 | 0.2378 | 0.6390 | 0.8613 |
| custom_lexical_fulltext | 0.3302 | 0.5077 | 0.2853 | 0.7394 | 0.9245 |
| rrf_bm25_ta_dense_ta | 0.2665 | 0.4544 | 0.2203 | 0.6701 | 0.9023 |
| rrf_bm25_ft_dense_ta | 0.3175 | 0.5173 | 0.2749 | 0.7806 | 0.9667 |
| rrf_bm25_ta_bm25_ft_dense_ta | 0.3028 | 0.5084 | 0.2572 | 0.7870 | 0.9806 |

## Notes

- `rrf_bm25_ta_dense_ta` fuses BM25 title+abstract with dense title+abstract.
- `rrf_bm25_ft_dense_ta` fuses BM25 fulltext with dense title+abstract.
- `rrf_bm25_ta_bm25_ft_dense_ta` fuses all three current first-stage runs.
- These runs reuse existing outputs only; they do not rebuild any index.
