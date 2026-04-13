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
| official_pyterrier_dctr | march_april->march_april_may | 0.2533 | 0.3235 | 0.3235 | 0.2884 | -0.2771 | 0.0000 | 1.0000 |
| custom_title_abstract_rm3_dctr | march_april->march_april_may | 0.2357 | 0.2822 | 0.2822 | 0.2589 | -0.1972 | 0.0799 | 0.7117 |
| custom_title_abstract_rerank_dctr | march_april->march_april_may | 0.2376 | 0.2757 | 0.2757 | 0.2566 | -0.1605 | 0.1167 | 0.5791 |
| custom_title_abstract_rerank_temporal_dctr | march_april->march_april_may | 0.2678 | 0.3052 | 0.3052 | 0.2865 | -0.1397 | 0.1375 | 0.5039 |
| custom_lexical_fulltext_dctr | march_april->march_april_may | 0.3220 | 0.3589 | 0.3589 | 0.3405 | -0.1146 | 0.1625 | 0.4136 |
| official_pyterrier_dense_temporal_dctr | march_april->march_april_may | 0.2714 | 0.2861 | 0.2861 | 0.2787 | -0.0544 | 0.2228 | 0.1962 |
| rrf_bm25_ta_dense_ta_dctr | march_april->march_april_may | 0.2534 | 0.2630 | 0.2630 | 0.2582 | -0.0381 | 0.2391 | 0.1374 |
| rrf_bm25_ft_dense_ta_dctr | march_april->march_april_may | 0.3246 | 0.3368 | 0.3368 | 0.3307 | -0.0378 | 0.2393 | 0.1365 |
| official_pyterrier_dense_dctr | march_april->march_april_may | 0.2686 | 0.2719 | 0.2719 | 0.2702 | -0.0121 | 0.2651 | 0.0435 |
| rrf_bm25_ta_bm25_ft_dense_ta_dctr | march_april->march_april_may | 0.3136 | 0.3170 | 0.3170 | 0.3153 | -0.0110 | 0.2661 | 0.0397 |
| official_pyterrier_temporal_dctr | march_april->march_april_may | 0.0149 | 0.0132 | 0.0132 | 0.0140 | 0.1171 | 0.3943 | -0.4227 |
| custom_title_abstract_rm3_temporal_dctr | march_april->march_april_may | 0.0234 | 0.0171 | 0.0171 | 0.0202 | 0.2705 | 0.5476 | -0.9759 |
| custom_lexical_fulltext_temporal_dctr | march_april->march_april_may | 0.0197 | 0.0135 | 0.0135 | 0.0166 | 0.3161 | 0.5933 | -1.1407 |
| custom_title_abstract_rm3_temporal_dctr | march_only->march_april | 0.0089 | 0.0234 | 0.0234 | 0.0162 | -1.6199 | -1.5280 | 17.6400 |
| official_pyterrier_temporal_dctr | march_only->march_april | 0.0103 | 0.0149 | 0.0149 | 0.0126 | -0.4531 | -0.3612 | 4.9338 |
| official_pyterrier_dense_temporal_dctr | march_only->march_april | 0.2074 | 0.2714 | 0.2714 | 0.2394 | -0.3083 | -0.2165 | 3.3578 |
| rrf_bm25_ta_dense_ta_dctr | march_only->march_april | 0.2041 | 0.2534 | 0.2534 | 0.2287 | -0.2412 | -0.1494 | 2.6267 |
| official_pyterrier_dense_dctr | march_only->march_april | 0.2188 | 0.2686 | 0.2686 | 0.2437 | -0.2275 | -0.1357 | 2.4779 |
| custom_title_abstract_rm3_dctr | march_only->march_april | 0.1961 | 0.2357 | 0.2357 | 0.2159 | -0.2019 | -0.1100 | 2.1981 |
| rrf_bm25_ft_dense_ta_dctr | march_only->march_april | 0.2728 | 0.3246 | 0.3246 | 0.2987 | -0.1898 | -0.0979 | 2.0666 |
| rrf_bm25_ta_bm25_ft_dense_ta_dctr | march_only->march_april | 0.2666 | 0.3136 | 0.3136 | 0.2901 | -0.1760 | -0.0842 | 1.9168 |
| custom_title_abstract_rerank_temporal_dctr | march_only->march_april | 0.2307 | 0.2678 | 0.2678 | 0.2493 | -0.1607 | -0.0688 | 1.7496 |
| custom_title_abstract_rerank_dctr | march_only->march_april | 0.2064 | 0.2376 | 0.2376 | 0.2220 | -0.1512 | -0.0593 | 1.6462 |
| custom_lexical_fulltext_dctr | march_only->march_april | 0.2874 | 0.3220 | 0.3220 | 0.3047 | -0.1204 | -0.0286 | 1.3114 |
| official_pyterrier_dctr | march_only->march_april | 0.2320 | 0.2533 | 0.2533 | 0.2426 | -0.0918 | 0.0000 | 1.0000 |
| custom_lexical_fulltext_temporal_dctr | march_only->march_april | 0.0186 | 0.0197 | 0.0197 | 0.0191 | -0.0616 | 0.0303 | 0.6704 |
| custom_title_abstract_rm3_temporal_dctr | march_only->march_april_may | 0.0089 | 0.0171 | 0.0171 | 0.0130 | -0.9113 | -0.5168 | 2.3104 |
| custom_title_abstract_rm3_dctr | march_only->march_april_may | 0.1961 | 0.2822 | 0.2822 | 0.2391 | -0.4389 | -0.0445 | 1.1128 |
| official_pyterrier_dctr | march_only->march_april_may | 0.2320 | 0.3235 | 0.3235 | 0.2777 | -0.3944 | 0.0000 | 1.0000 |
| official_pyterrier_dense_temporal_dctr | march_only->march_april_may | 0.2074 | 0.2861 | 0.2861 | 0.2468 | -0.3795 | 0.0149 | 0.9622 |
| custom_title_abstract_rerank_dctr | march_only->march_april_may | 0.2064 | 0.2757 | 0.2757 | 0.2410 | -0.3359 | 0.0585 | 0.8517 |
| custom_title_abstract_rerank_temporal_dctr | march_only->march_april_may | 0.2307 | 0.3052 | 0.3052 | 0.2680 | -0.3228 | 0.0717 | 0.8183 |
| rrf_bm25_ta_dense_ta_dctr | march_only->march_april_may | 0.2041 | 0.2630 | 0.2630 | 0.2336 | -0.2885 | 0.1060 | 0.7313 |
| official_pyterrier_temporal_dctr | march_only->march_april_may | 0.0103 | 0.0132 | 0.0132 | 0.0117 | -0.2828 | 0.1116 | 0.7171 |
| custom_lexical_fulltext_dctr | march_only->march_april_may | 0.2874 | 0.3589 | 0.3589 | 0.3232 | -0.2488 | 0.1456 | 0.6309 |
| official_pyterrier_dense_dctr | march_only->march_april_may | 0.2188 | 0.2719 | 0.2719 | 0.2453 | -0.2424 | 0.1521 | 0.6145 |
| rrf_bm25_ft_dense_ta_dctr | march_only->march_april_may | 0.2728 | 0.3368 | 0.3368 | 0.3048 | -0.2348 | 0.1596 | 0.5953 |
| rrf_bm25_ta_bm25_ft_dense_ta_dctr | march_only->march_april_may | 0.2666 | 0.3170 | 0.3170 | 0.2918 | -0.1890 | 0.2055 | 0.4791 |
| custom_lexical_fulltext_temporal_dctr | march_only->march_april_may | 0.0186 | 0.0135 | 0.0135 | 0.0160 | 0.2740 | 0.6684 | -0.6948 |
