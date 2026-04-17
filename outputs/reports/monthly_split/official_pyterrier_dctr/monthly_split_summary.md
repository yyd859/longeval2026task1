# Snapshot-1 Month Split Evaluation

| Split | Date Field | Months | Queries | Docs | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| march_only | createdDate | 3 | 78 | 49631 | 0.1934 | 0.2098 | 0.1816 | 0.2906 | 0.2906 |
| march_april | createdDate | 3,4 | 93 | 134355 | 0.2417 | 0.2753 | 0.2134 | 0.4481 | 0.4643 |
| march_april_may | createdDate | 3,4,5 | 97 | 232307 | 0.2878 | 0.3349 | 0.2471 | 0.5396 | 0.5552 |