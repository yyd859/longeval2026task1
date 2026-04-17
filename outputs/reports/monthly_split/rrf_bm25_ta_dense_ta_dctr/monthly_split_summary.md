# Snapshot-1 Month Split Evaluation

| Split | Date Field | Months | Queries | Docs | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| march_only | createdDate | 3 | 78 | 49631 | 0.2022 | 0.2285 | 0.1868 | 0.3526 | 0.3526 |
| march_april | createdDate | 3,4 | 93 | 134355 | 0.2347 | 0.2758 | 0.1954 | 0.4650 | 0.5212 |
| march_april_may | createdDate | 3,4,5 | 97 | 232307 | 0.2624 | 0.3221 | 0.2111 | 0.5323 | 0.6166 |