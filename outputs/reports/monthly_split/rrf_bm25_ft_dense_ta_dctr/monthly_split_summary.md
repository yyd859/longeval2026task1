# Snapshot-1 Month Split Evaluation

| Split | Date Field | Months | Queries | Docs | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| march_only | publishedDate | 3 | 74 | 173031 | 0.2732 | 0.2983 | 0.2421 | 0.4437 | 0.4572 |
| march_april | publishedDate | 3,4 | 92 | 343421 | 0.2849 | 0.3322 | 0.2382 | 0.5639 | 0.6076 |
| march_april_may | publishedDate | 3,4,5 | 96 | 525293 | 0.2930 | 0.3703 | 0.2488 | 0.6109 | 0.6799 |