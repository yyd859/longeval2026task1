# Snapshot-1 Month Split Evaluation

| Split | Date Field | Months | Queries | Docs | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| march_only | publishedDate | 3 | 74 | 173031 | 0.2427 | 0.2632 | 0.1962 | 0.4437 | 0.4572 |
| march_april | publishedDate | 3,4 | 92 | 343421 | 0.2138 | 0.2830 | 0.1790 | 0.5678 | 0.6283 |
| march_april_may | publishedDate | 3,4,5 | 96 | 525293 | 0.2526 | 0.3468 | 0.2191 | 0.6079 | 0.6910 |