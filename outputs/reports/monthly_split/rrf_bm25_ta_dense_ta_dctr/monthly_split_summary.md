# Snapshot-1 Month Split Evaluation

| Split | Date Field | Months | Queries | Docs | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| march_only | publishedDate | 3 | 74 | 173031 | 0.1961 | 0.2251 | 0.1555 | 0.4279 | 0.4302 |
| march_april | publishedDate | 3,4 | 92 | 343421 | 0.1902 | 0.2527 | 0.1561 | 0.5368 | 0.5833 |
| march_april_may | publishedDate | 3,4,5 | 96 | 525293 | 0.2300 | 0.3039 | 0.1845 | 0.5395 | 0.6312 |