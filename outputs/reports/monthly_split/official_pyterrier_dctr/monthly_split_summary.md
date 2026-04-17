# Snapshot-1 Month Split Evaluation

| Split | Date Field | Months | Queries | Docs | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| march_only | publishedDate | 3 | 74 | 173031 | 0.1767 | 0.2024 | 0.1518 | 0.3491 | 0.3559 |
| march_april | publishedDate | 3,4 | 92 | 343421 | 0.2047 | 0.2557 | 0.1786 | 0.4694 | 0.5165 |
| march_april_may | publishedDate | 3,4,5 | 96 | 525293 | 0.2377 | 0.3077 | 0.2048 | 0.5432 | 0.5909 |