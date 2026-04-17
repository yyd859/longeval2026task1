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
| custom_title_abstract_rm3_temporal_dctr | march_april->march_april_may | 0.0026 | 0.0128 | 0.0128 | 0.0077 | -4.0216 | -3.8602 | 24.9161 |
| official_pyterrier_temporal_dctr | march_april->march_april_may | 0.0033 | 0.0089 | 0.0089 | 0.0061 | -1.6774 | -1.5160 | 10.3923 |
| official_pyterrier_temporal_citation_dctr | march_april->march_april_may | 0.0033 | 0.0071 | 0.0071 | 0.0052 | -1.1360 | -0.9746 | 7.0380 |
| custom_title_abstract_rerank_dctr | march_april->march_april_may | 0.2172 | 0.2655 | 0.2655 | 0.2413 | -0.2228 | -0.0614 | 1.3802 |
| rrf_bm25_ta_dense_ta_dctr | march_april->march_april_may | 0.1902 | 0.2300 | 0.2300 | 0.2101 | -0.2090 | -0.0476 | 1.2950 |
| custom_title_abstract_rm3_dctr | march_april->march_april_may | 0.1883 | 0.2273 | 0.2273 | 0.2078 | -0.2068 | -0.0454 | 1.2814 |
| custom_title_abstract_rerank_temporal_citation_dctr | march_april->march_april_may | 0.1827 | 0.2165 | 0.2165 | 0.1996 | -0.1851 | -0.0237 | 1.1470 |
| rrf_bm25_ta_bm25_ft_dense_ta_dctr | march_april->march_april_may | 0.2138 | 0.2526 | 0.2526 | 0.2332 | -0.1813 | -0.0199 | 1.1233 |
| official_pyterrier_dctr | march_april->march_april_may | 0.2047 | 0.2377 | 0.2377 | 0.2212 | -0.1614 | 0.0000 | 1.0000 |
| custom_title_abstract_rerank_temporal_dctr | march_april->march_april_may | 0.1937 | 0.2237 | 0.2237 | 0.2087 | -0.1550 | 0.0064 | 0.9605 |
| custom_lexical_fulltext_dctr | march_april->march_april_may | 0.2259 | 0.2495 | 0.2495 | 0.2377 | -0.1047 | 0.0567 | 0.6489 |
| official_pyterrier_dense_dctr | march_april->march_april_may | 0.2182 | 0.2316 | 0.2316 | 0.2249 | -0.0614 | 0.1000 | 0.3805 |
| official_pyterrier_dense_temporal_dctr | march_april->march_april_may | 0.2792 | 0.2917 | 0.2917 | 0.2855 | -0.0447 | 0.1167 | 0.2771 |
| rrf_bm25_ft_dense_ta_dctr | march_april->march_april_may | 0.2849 | 0.2930 | 0.2930 | 0.2889 | -0.0287 | 0.1327 | 0.1778 |
| custom_lexical_fulltext_temporal_citation_dctr | march_april->march_april_may | 0.0064 | 0.0063 | 0.0063 | 0.0063 | 0.0166 | 0.1780 | -0.1028 |
| custom_lexical_fulltext_temporal_dctr | march_april->march_april_may | 0.0064 | 0.0063 | 0.0063 | 0.0063 | 0.0166 | 0.1780 | -0.1028 |
| custom_title_abstract_rerank_dctr | march_only->march_april | 0.1728 | 0.2172 | 0.2172 | 0.1950 | -0.2565 | -0.0985 | 1.6234 |
| official_pyterrier_dense_temporal_dctr | march_only->march_april | 0.2241 | 0.2792 | 0.2792 | 0.2517 | -0.2460 | -0.0880 | 1.5572 |
| custom_title_abstract_rerank_temporal_dctr | march_only->march_april | 0.1571 | 0.1937 | 0.1937 | 0.1754 | -0.2324 | -0.0744 | 1.4708 |
| official_pyterrier_temporal_citation_dctr | march_only->march_april | 0.0028 | 0.0033 | 0.0033 | 0.0030 | -0.2065 | -0.0485 | 1.3073 |
| official_pyterrier_temporal_dctr | march_only->march_april | 0.0028 | 0.0033 | 0.0033 | 0.0030 | -0.2065 | -0.0485 | 1.3073 |
| custom_title_abstract_rm3_dctr | march_only->march_april | 0.1580 | 0.1883 | 0.1883 | 0.1732 | -0.1916 | -0.0336 | 1.2128 |
| custom_title_abstract_rerank_temporal_citation_dctr | march_only->march_april | 0.1576 | 0.1827 | 0.1827 | 0.1702 | -0.1589 | -0.0009 | 1.0056 |
| official_pyterrier_dctr | march_only->march_april | 0.1767 | 0.2047 | 0.2047 | 0.1907 | -0.1580 | 0.0000 | 1.0000 |
| official_pyterrier_dense_dctr | march_only->march_april | 0.2009 | 0.2182 | 0.2182 | 0.2095 | -0.0864 | 0.0716 | 0.5470 |
| rrf_bm25_ft_dense_ta_dctr | march_only->march_april | 0.2732 | 0.2849 | 0.2849 | 0.2790 | -0.0426 | 0.1154 | 0.2694 |
| custom_lexical_fulltext_dctr | march_only->march_april | 0.2314 | 0.2259 | 0.2259 | 0.2286 | 0.0238 | 0.1818 | -0.1509 |
| rrf_bm25_ta_dense_ta_dctr | march_only->march_april | 0.1961 | 0.1902 | 0.1902 | 0.1931 | 0.0298 | 0.1878 | -0.1886 |
| rrf_bm25_ta_bm25_ft_dense_ta_dctr | march_only->march_april | 0.2427 | 0.2138 | 0.2138 | 0.2283 | 0.1190 | 0.2770 | -0.7531 |
| custom_title_abstract_rm3_temporal_dctr | march_only->march_april | 0.0052 | 0.0026 | 0.0026 | 0.0039 | 0.5121 | 0.6701 | -3.2418 |
| custom_lexical_fulltext_temporal_citation_dctr | march_only->march_april | 0.0189 | 0.0064 | 0.0064 | 0.0126 | 0.6613 | 0.8193 | -4.1862 |
| custom_lexical_fulltext_temporal_dctr | march_only->march_april | 0.0189 | 0.0064 | 0.0064 | 0.0126 | 0.6613 | 0.8193 | -4.1862 |
| official_pyterrier_temporal_dctr | march_only->march_april_may | 0.0028 | 0.0089 | 0.0089 | 0.0058 | -2.2303 | -1.8854 | 6.4669 |
| official_pyterrier_temporal_citation_dctr | march_only->march_april_may | 0.0028 | 0.0071 | 0.0071 | 0.0049 | -1.5771 | -1.2322 | 4.5728 |
| custom_title_abstract_rm3_temporal_dctr | march_only->march_april_may | 0.0052 | 0.0128 | 0.0128 | 0.0090 | -1.4498 | -1.1050 | 4.2039 |
| custom_title_abstract_rerank_dctr | march_only->march_april_may | 0.1728 | 0.2655 | 0.2655 | 0.2192 | -0.5364 | -0.1915 | 1.5552 |
| custom_title_abstract_rm3_dctr | march_only->march_april_may | 0.1580 | 0.2273 | 0.2273 | 0.1926 | -0.4380 | -0.0932 | 1.2701 |
| custom_title_abstract_rerank_temporal_dctr | march_only->march_april_may | 0.1571 | 0.2237 | 0.2237 | 0.1904 | -0.4234 | -0.0785 | 1.2277 |
| custom_title_abstract_rerank_temporal_citation_dctr | march_only->march_april_may | 0.1576 | 0.2165 | 0.2165 | 0.1871 | -0.3734 | -0.0285 | 1.0828 |
| official_pyterrier_dctr | march_only->march_april_may | 0.1767 | 0.2377 | 0.2377 | 0.2072 | -0.3449 | 0.0000 | 1.0000 |
| official_pyterrier_dense_temporal_dctr | march_only->march_april_may | 0.2241 | 0.2917 | 0.2917 | 0.2579 | -0.3017 | 0.0432 | 0.8749 |
| rrf_bm25_ta_dense_ta_dctr | march_only->march_april_may | 0.1961 | 0.2300 | 0.2300 | 0.2130 | -0.1730 | 0.1719 | 0.5016 |
| official_pyterrier_dense_dctr | march_only->march_april_may | 0.2009 | 0.2316 | 0.2316 | 0.2162 | -0.1531 | 0.1917 | 0.4440 |
| custom_lexical_fulltext_dctr | march_only->march_april_may | 0.2314 | 0.2495 | 0.2495 | 0.2405 | -0.0784 | 0.2665 | 0.2273 |
| rrf_bm25_ft_dense_ta_dctr | march_only->march_april_may | 0.2732 | 0.2930 | 0.2930 | 0.2831 | -0.0725 | 0.2724 | 0.2102 |
| rrf_bm25_ta_bm25_ft_dense_ta_dctr | march_only->march_april_may | 0.2427 | 0.2526 | 0.2526 | 0.2477 | -0.0408 | 0.3041 | 0.1182 |
| custom_lexical_fulltext_temporal_citation_dctr | march_only->march_april_may | 0.0189 | 0.0063 | 0.0063 | 0.0126 | 0.6669 | 1.0118 | -1.9338 |
| custom_lexical_fulltext_temporal_dctr | march_only->march_april_may | 0.0189 | 0.0063 | 0.0063 | 0.0126 | 0.6669 | 1.0118 | -1.9338 |
