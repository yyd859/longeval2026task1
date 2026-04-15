# Snapshot-1 Train Comparison Across All Current Models

Total current models in this report: `16`

Model families:
- 5 base models
- 5 temporal sibling models
- 3 citation-aware temporal sibling models
- 3 RRF fusion models

## DCTR Results

| Method | Family | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| custom_lexical_fulltext | base | 0.3302 | 0.5077 | 0.2853 | 0.7394 | 0.9245 |
| custom_title_abstract_rerank | base | 0.3222 | 0.4821 | 0.2777 | 0.6952 | 0.8581 |
| rrf_bm25_ft_dense_ta | fusion | 0.3175 | 0.5173 | 0.2749 | 0.7806 | 0.9667 |
| official_pyterrier_dense_temporal | temporal | 0.3101 | 0.4659 | 0.2598 | 0.6423 | 0.8613 |
| rrf_bm25_ta_bm25_ft_dense_ta | fusion | 0.3028 | 0.5084 | 0.2572 | 0.7870 | 0.9806 |
| official_pyterrier | base | 0.2922 | 0.4564 | 0.2573 | 0.6836 | 0.8581 |
| official_pyterrier_dense | base | 0.2820 | 0.4483 | 0.2378 | 0.6390 | 0.8613 |
| custom_title_abstract_rm3 | base | 0.2781 | 0.4510 | 0.2402 | 0.6559 | 0.8701 |
| custom_title_abstract_rerank_temporal | temporal | 0.2677 | 0.4300 | 0.2349 | 0.5438 | 0.8581 |
| rrf_bm25_ta_dense_ta | fusion | 0.2665 | 0.4544 | 0.2203 | 0.6701 | 0.9023 |
| custom_title_abstract_rerank_temporal_citation | temporal_citation | 0.2562 | 0.4187 | 0.2215 | 0.5440 | 0.8581 |
| custom_title_abstract_rm3_temporal | temporal | 0.0154 | 0.1842 | 0.0144 | 0.0433 | 0.8701 |
| custom_lexical_fulltext_temporal | temporal | 0.0088 | 0.1935 | 0.0091 | 0.0213 | 0.9245 |
| custom_lexical_fulltext_temporal_citation | temporal_citation | 0.0088 | 0.1935 | 0.0091 | 0.0213 | 0.9245 |
| official_pyterrier_temporal | temporal | 0.0053 | 0.1750 | 0.0083 | 0.0298 | 0.8581 |
| official_pyterrier_temporal_citation | temporal_citation | 0.0046 | 0.1749 | 0.0085 | 0.0298 | 0.8581 |

## Raw Results

| Method | Family | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| custom_lexical_fulltext | base | 0.3637 | 0.5504 | 0.2899 | 0.7324 | 0.9205 |
| rrf_bm25_ft_dense_ta | fusion | 0.3532 | 0.5648 | 0.2887 | 0.7741 | 0.9609 |
| official_pyterrier_dense_temporal | temporal | 0.3433 | 0.5075 | 0.2657 | 0.6371 | 0.8555 |
| custom_title_abstract_rerank | base | 0.3373 | 0.5152 | 0.2750 | 0.6836 | 0.8561 |
| rrf_bm25_ta_bm25_ft_dense_ta | fusion | 0.3343 | 0.5563 | 0.2714 | 0.7873 | 0.9747 |
| official_pyterrier | base | 0.3310 | 0.5034 | 0.2658 | 0.6831 | 0.8561 |
| official_pyterrier_dense | base | 0.3106 | 0.4875 | 0.2402 | 0.6379 | 0.8555 |
| custom_title_abstract_rm3 | base | 0.3074 | 0.4934 | 0.2469 | 0.6534 | 0.8688 |
| rrf_bm25_ta_dense_ta | fusion | 0.2993 | 0.4988 | 0.2330 | 0.6666 | 0.8990 |
| custom_title_abstract_rerank_temporal | temporal | 0.2882 | 0.4647 | 0.2375 | 0.5474 | 0.8561 |
| custom_title_abstract_rerank_temporal_citation | temporal_citation | 0.2731 | 0.4514 | 0.2224 | 0.5449 | 0.8561 |
| custom_title_abstract_rm3_temporal | temporal | 0.0129 | 0.2009 | 0.0107 | 0.0377 | 0.8688 |
| custom_lexical_fulltext_temporal | temporal | 0.0095 | 0.2130 | 0.0095 | 0.0217 | 0.9205 |
| custom_lexical_fulltext_temporal_citation | temporal_citation | 0.0095 | 0.2130 | 0.0094 | 0.0217 | 0.9205 |
| official_pyterrier_temporal_citation | temporal_citation | 0.0056 | 0.1949 | 0.0090 | 0.0304 | 0.8561 |
| official_pyterrier_temporal | temporal | 0.0055 | 0.1948 | 0.0089 | 0.0304 | 0.8561 |

