# Snapshot-1 Month Split Evaluation

| Split | Date Field | Months | Queries | Docs | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| march_only | publishedDate | 3 | 74 | 173031 | 0.1728 | 0.2013 | 0.1460 | 0.3559 | 0.3559 |
| march_april | publishedDate | 3,4 | 92 | 343421 | 0.2172 | 0.2639 | 0.1839 | 0.4730 | 0.5165 |
| march_april_may | publishedDate | 3,4,5 | 96 | 525293 | 0.2655 | 0.3258 | 0.2224 | 0.5237 | 0.5909 |