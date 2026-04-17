# Snapshot-1 Month Split Evaluation

| Split | Date Field | Months | Queries | Docs | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| march_only | createdDate | 3 | 78 | 49631 | 0.2316 | 0.2529 | 0.2113 | 0.3846 | 0.3846 |
| march_april | createdDate | 3,4 | 93 | 134355 | 0.2710 | 0.3096 | 0.2233 | 0.5152 | 0.5515 |
| march_april_may | createdDate | 3,4,5 | 97 | 232307 | 0.2885 | 0.3593 | 0.2353 | 0.6124 | 0.6652 |