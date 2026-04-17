# Snapshot-1 Month Split Evaluation

| Split | Date Field | Months | Queries | Docs | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| march_only | publishedDate | 3 | 74 | 173031 | 0.2314 | 0.2611 | 0.1952 | 0.4527 | 0.4595 |
| march_april | publishedDate | 3,4 | 92 | 343421 | 0.2259 | 0.2863 | 0.1891 | 0.5580 | 0.5906 |
| march_april_may | publishedDate | 3,4,5 | 96 | 525293 | 0.2495 | 0.3390 | 0.2151 | 0.5995 | 0.6525 |