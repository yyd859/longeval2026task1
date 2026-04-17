# Snapshot-1 Month Split Evaluation

| Split | Date Field | Months | Queries | Docs | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| march_only | createdDate | 3 | 78 | 49631 | 0.2049 | 0.2101 | 0.1789 | 0.2906 | 0.2906 |
| march_april | createdDate | 3,4 | 93 | 134355 | 0.2617 | 0.2899 | 0.2274 | 0.4643 | 0.4643 |
| march_april_may | createdDate | 3,4,5 | 97 | 232307 | 0.2751 | 0.3243 | 0.2392 | 0.5371 | 0.5552 |