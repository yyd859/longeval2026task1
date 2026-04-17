# Snapshot-1 Month Split Evaluation

| Split | Date Field | Months | Queries | Docs | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| march_only | createdDate | 3 | 78 | 49631 | 0.1916 | 0.2023 | 0.1705 | 0.2906 | 0.2906 |
| march_april | createdDate | 3,4 | 93 | 134355 | 0.2396 | 0.2750 | 0.2149 | 0.4589 | 0.4643 |
| march_april_may | createdDate | 3,4,5 | 97 | 232307 | 0.2382 | 0.3004 | 0.2166 | 0.5285 | 0.5552 |