# Snapshot-1 Month Split Evaluation

| Split | Date Field | Months | Queries | Docs | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| march_only | publishedDate | 3 | 74 | 173031 | 0.0028 | 0.0557 | 0.0041 | 0.0518 | 0.3559 |
| march_april | publishedDate | 3,4 | 92 | 343421 | 0.0033 | 0.0762 | 0.0052 | 0.0417 | 0.5165 |
| march_april_may | publishedDate | 3,4,5 | 96 | 525293 | 0.0089 | 0.0931 | 0.0077 | 0.0352 | 0.5909 |