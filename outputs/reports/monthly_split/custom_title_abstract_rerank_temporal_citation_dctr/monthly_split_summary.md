# Snapshot-1 Month Split Evaluation

| Split | Date Field | Months | Queries | Docs | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| march_only | publishedDate | 3 | 74 | 173031 | 0.1576 | 0.1828 | 0.1299 | 0.3559 | 0.3559 |
| march_april | publishedDate | 3,4 | 92 | 343421 | 0.1827 | 0.2395 | 0.1603 | 0.4295 | 0.5165 |
| march_april_may | publishedDate | 3,4,5 | 96 | 525293 | 0.2165 | 0.2944 | 0.1951 | 0.4957 | 0.5909 |