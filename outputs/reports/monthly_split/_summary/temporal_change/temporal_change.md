# Temporal Change Report

Primary score metric: `ndcg_cut_10`
Pivot model: `official_pyterrier_dctr`

Definitions:
- `ARP`: score at the later split in the transition.
- `MARP`: mean score across the earlier and later splits.
- `RI`: `(earlier - later) / earlier`; lower is more robust, negative means improvement.
- `DRI`: `RI(system) - RI(pivot)`.
- `ER`: `RI(system) / RI(pivot)` with a small denominator floor.

| Model | Transition | Earlier | Later | ARP | MARP | RI | DRI | ER |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| custom_title_abstract_rm3_temporal_dctr | march_april->march_april_may | 0.0038 | 0.0103 | 0.0103 | 0.0071 | -1.6916 | -1.5010 | 8.8762 |
| official_pyterrier_temporal_citation_dctr | march_april->march_april_may | 0.0059 | 0.0071 | 0.0071 | 0.0065 | -0.2032 | -0.0126 | 1.0663 |
| official_pyterrier_dctr | march_april->march_april_may | 0.2417 | 0.2878 | 0.2878 | 0.2647 | -0.1906 | 0.0000 | 1.0000 |
| custom_title_abstract_rm3_dctr | march_april->march_april_may | 0.2365 | 0.2798 | 0.2798 | 0.2582 | -0.1831 | 0.0075 | 0.9605 |
| custom_lexical_fulltext_dctr | march_april->march_april_may | 0.2457 | 0.2775 | 0.2775 | 0.2616 | -0.1294 | 0.0612 | 0.6788 |
| official_pyterrier_temporal_dctr | march_april->march_april_may | 0.0067 | 0.0076 | 0.0076 | 0.0072 | -0.1273 | 0.0632 | 0.6682 |
| official_pyterrier_dense_temporal_dctr | march_april->march_april_may | 0.2560 | 0.2883 | 0.2883 | 0.2722 | -0.1263 | 0.0643 | 0.6625 |
| rrf_bm25_ta_dense_ta_dctr | march_april->march_april_may | 0.2347 | 0.2624 | 0.2624 | 0.2486 | -0.1177 | 0.0729 | 0.6176 |
| official_pyterrier_dense_dctr | march_april->march_april_may | 0.2445 | 0.2710 | 0.2710 | 0.2578 | -0.1081 | 0.0825 | 0.5673 |
| rrf_bm25_ft_dense_ta_dctr | march_april->march_april_may | 0.2741 | 0.2965 | 0.2965 | 0.2853 | -0.0817 | 0.1089 | 0.4288 |
| rrf_bm25_ta_bm25_ft_dense_ta_dctr | march_april->march_april_may | 0.2710 | 0.2885 | 0.2885 | 0.2798 | -0.0646 | 0.1260 | 0.3391 |
| custom_title_abstract_rerank_dctr | march_april->march_april_may | 0.2617 | 0.2751 | 0.2751 | 0.2684 | -0.0509 | 0.1396 | 0.2673 |
| custom_title_abstract_rerank_temporal_citation_dctr | march_april->march_april_may | 0.2416 | 0.2410 | 0.2410 | 0.2413 | 0.0025 | 0.1930 | -0.0129 |
| custom_title_abstract_rerank_temporal_dctr | march_april->march_april_may | 0.2396 | 0.2382 | 0.2382 | 0.2389 | 0.0055 | 0.1960 | -0.0287 |
| custom_lexical_fulltext_temporal_citation_dctr | march_april->march_april_may | 0.0185 | 0.0102 | 0.0102 | 0.0144 | 0.4477 | 0.6383 | -2.3492 |
| custom_lexical_fulltext_temporal_dctr | march_april->march_april_may | 0.0185 | 0.0102 | 0.0102 | 0.0144 | 0.4477 | 0.6383 | -2.3492 |
| official_pyterrier_temporal_dctr | march_only->march_april | 0.0015 | 0.0067 | 0.0067 | 0.0041 | -3.5841 | -3.3343 | 14.3532 |
| official_pyterrier_temporal_citation_dctr | march_only->march_april | 0.0015 | 0.0059 | 0.0059 | 0.0037 | -2.9956 | -2.7459 | 11.9966 |
| custom_lexical_fulltext_temporal_citation_dctr | march_only->march_april | 0.0107 | 0.0185 | 0.0185 | 0.0146 | -0.7385 | -0.4888 | 2.9575 |
| custom_lexical_fulltext_temporal_dctr | march_only->march_april | 0.0107 | 0.0185 | 0.0185 | 0.0146 | -0.7385 | -0.4888 | 2.9575 |
| custom_title_abstract_rm3_dctr | march_only->march_april | 0.1817 | 0.2365 | 0.2365 | 0.2091 | -0.3019 | -0.0522 | 1.2091 |
| official_pyterrier_dense_temporal_dctr | march_only->march_april | 0.1974 | 0.2560 | 0.2560 | 0.2267 | -0.2967 | -0.0470 | 1.1883 |
| custom_title_abstract_rerank_dctr | march_only->march_april | 0.2049 | 0.2617 | 0.2617 | 0.2333 | -0.2774 | -0.0277 | 1.1107 |
| custom_title_abstract_rerank_temporal_citation_dctr | march_only->march_april | 0.1896 | 0.2416 | 0.2416 | 0.2156 | -0.2743 | -0.0246 | 1.0986 |
| custom_title_abstract_rerank_temporal_dctr | march_only->march_april | 0.1916 | 0.2396 | 0.2396 | 0.2156 | -0.2501 | -0.0004 | 1.0017 |
| official_pyterrier_dctr | march_only->march_april | 0.1934 | 0.2417 | 0.2417 | 0.2176 | -0.2497 | 0.0000 | 1.0000 |
| official_pyterrier_dense_dctr | march_only->march_april | 0.2019 | 0.2445 | 0.2445 | 0.2232 | -0.2114 | 0.0383 | 0.8465 |
| rrf_bm25_ta_bm25_ft_dense_ta_dctr | march_only->march_april | 0.2316 | 0.2710 | 0.2710 | 0.2513 | -0.1701 | 0.0796 | 0.6813 |
| rrf_bm25_ta_dense_ta_dctr | march_only->march_april | 0.2022 | 0.2347 | 0.2347 | 0.2185 | -0.1610 | 0.0887 | 0.6448 |
| rrf_bm25_ft_dense_ta_dctr | march_only->march_april | 0.2546 | 0.2741 | 0.2741 | 0.2644 | -0.0766 | 0.1731 | 0.3068 |
| custom_lexical_fulltext_dctr | march_only->march_april | 0.2366 | 0.2457 | 0.2457 | 0.2412 | -0.0384 | 0.2113 | 0.1538 |
| custom_title_abstract_rm3_temporal_dctr | march_only->march_april | 0.0111 | 0.0038 | 0.0038 | 0.0075 | 0.6563 | 0.9060 | -2.6282 |
| official_pyterrier_temporal_dctr | march_only->march_april_may | 0.0015 | 0.0076 | 0.0076 | 0.0045 | -4.1678 | -3.6799 | 8.5428 |
| official_pyterrier_temporal_citation_dctr | march_only->march_april_may | 0.0015 | 0.0071 | 0.0071 | 0.0043 | -3.8075 | -3.3196 | 7.8044 |
| custom_title_abstract_rm3_dctr | march_only->march_april_may | 0.1817 | 0.2798 | 0.2798 | 0.2308 | -0.5402 | -0.0524 | 1.1073 |
| official_pyterrier_dctr | march_only->march_april_may | 0.1934 | 0.2878 | 0.2878 | 0.2406 | -0.4879 | 0.0000 | 1.0000 |
| official_pyterrier_dense_temporal_dctr | march_only->march_april_may | 0.1974 | 0.2883 | 0.2883 | 0.2429 | -0.4604 | 0.0274 | 0.9438 |
| custom_title_abstract_rerank_dctr | march_only->march_april_may | 0.2049 | 0.2751 | 0.2751 | 0.2400 | -0.3424 | 0.1455 | 0.7019 |
| official_pyterrier_dense_dctr | march_only->march_april_may | 0.2019 | 0.2710 | 0.2710 | 0.2364 | -0.3423 | 0.1455 | 0.7017 |
| rrf_bm25_ta_dense_ta_dctr | march_only->march_april_may | 0.2022 | 0.2624 | 0.2624 | 0.2323 | -0.2976 | 0.1902 | 0.6101 |
| custom_title_abstract_rerank_temporal_citation_dctr | march_only->march_april_may | 0.1896 | 0.2410 | 0.2410 | 0.2153 | -0.2712 | 0.2167 | 0.5559 |
| rrf_bm25_ta_bm25_ft_dense_ta_dctr | march_only->march_april_may | 0.2316 | 0.2885 | 0.2885 | 0.2601 | -0.2457 | 0.2421 | 0.5037 |
| custom_title_abstract_rerank_temporal_dctr | march_only->march_april_may | 0.1916 | 0.2382 | 0.2382 | 0.2149 | -0.2433 | 0.2446 | 0.4987 |
| custom_lexical_fulltext_dctr | march_only->march_april_may | 0.2366 | 0.2775 | 0.2775 | 0.2570 | -0.1727 | 0.3151 | 0.3540 |
| rrf_bm25_ft_dense_ta_dctr | march_only->march_april_may | 0.2546 | 0.2965 | 0.2965 | 0.2756 | -0.1646 | 0.3233 | 0.3373 |
| custom_lexical_fulltext_temporal_citation_dctr | march_only->march_april_may | 0.0107 | 0.0102 | 0.0102 | 0.0104 | 0.0398 | 0.5277 | -0.0816 |
| custom_lexical_fulltext_temporal_dctr | march_only->march_april_may | 0.0107 | 0.0102 | 0.0102 | 0.0104 | 0.0398 | 0.5277 | -0.0816 |
| custom_title_abstract_rm3_temporal_dctr | march_only->march_april_may | 0.0111 | 0.0103 | 0.0103 | 0.0107 | 0.0748 | 0.5627 | -0.1534 |
