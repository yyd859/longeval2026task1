# Snapshot-1 Month Split Evaluation

| Split | Date Field | Months | Queries | Docs | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| march_only | publishedDate | 3 | 74 | 173031 | 0.1580 | 0.1899 | 0.1315 | 0.3604 | 0.3739 |
| march_april | publishedDate | 3,4 | 92 | 343421 | 0.1883 | 0.2422 | 0.1570 | 0.5056 | 0.5299 |
| march_april_may | publishedDate | 3,4,5 | 96 | 525293 | 0.2273 | 0.3066 | 0.1944 | 0.5553 | 0.6042 |