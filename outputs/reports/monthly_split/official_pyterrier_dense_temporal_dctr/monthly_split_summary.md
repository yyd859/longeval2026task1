# Snapshot-1 Month Split Evaluation

| Split | Date Field | Months | Queries | Docs | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| march_only | createdDate | 3 | 78 | 49631 | 0.1974 | 0.2195 | 0.1795 | 0.3526 | 0.3526 |
| march_april | createdDate | 3,4 | 93 | 134355 | 0.2560 | 0.2897 | 0.2268 | 0.4232 | 0.4951 |
| march_april_may | createdDate | 3,4,5 | 97 | 232307 | 0.2883 | 0.3406 | 0.2553 | 0.4677 | 0.5795 |