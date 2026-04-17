# Snapshot-1 Month Split Evaluation

| Split | Date Field | Months | Queries | Docs | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| march_only | publishedDate | 3 | 74 | 173031 | 0.0052 | 0.0591 | 0.0062 | 0.0338 | 0.3739 |
| march_april | publishedDate | 3,4 | 92 | 343421 | 0.0026 | 0.0772 | 0.0047 | 0.0333 | 0.5299 |
| march_april_may | publishedDate | 3,4,5 | 96 | 525293 | 0.0128 | 0.0982 | 0.0136 | 0.0303 | 0.6042 |