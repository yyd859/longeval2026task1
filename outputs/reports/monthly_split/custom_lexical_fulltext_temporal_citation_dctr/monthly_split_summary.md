# Snapshot-1 Month Split Evaluation

| Split | Date Field | Months | Queries | Docs | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| march_only | publishedDate | 3 | 74 | 173031 | 0.0189 | 0.0925 | 0.0229 | 0.1239 | 0.4595 |
| march_april | publishedDate | 3,4 | 92 | 343421 | 0.0064 | 0.0943 | 0.0079 | 0.0752 | 0.5906 |
| march_april_may | publishedDate | 3,4,5 | 96 | 525293 | 0.0063 | 0.1058 | 0.0069 | 0.0346 | 0.6525 |