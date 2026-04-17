# Snapshot-1 Month Split Evaluation

| Split | Date Field | Months | Queries | Docs | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| march_only | createdDate | 3 | 78 | 49631 | 0.2019 | 0.2167 | 0.1706 | 0.3526 | 0.3526 |
| march_april | createdDate | 3,4 | 93 | 134355 | 0.2445 | 0.2825 | 0.2126 | 0.4710 | 0.4951 |
| march_april_may | createdDate | 3,4,5 | 97 | 232307 | 0.2710 | 0.3328 | 0.2393 | 0.5281 | 0.5795 |