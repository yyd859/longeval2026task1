# Snapshot-1 Month Split Evaluation

| Split | Date Field | Months | Queries | Docs | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| march_only | publishedDate | 3 | 74 | 173031 | 0.1571 | 0.1835 | 0.1294 | 0.3559 | 0.3559 |
| march_april | publishedDate | 3,4 | 92 | 343421 | 0.1937 | 0.2511 | 0.1748 | 0.4295 | 0.5165 |
| march_april_may | publishedDate | 3,4,5 | 96 | 525293 | 0.2237 | 0.3016 | 0.2049 | 0.4905 | 0.5909 |