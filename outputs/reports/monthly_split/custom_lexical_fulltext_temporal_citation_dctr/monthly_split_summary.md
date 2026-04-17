# Snapshot-1 Month Split Evaluation

| Split | Date Field | Months | Queries | Docs | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| march_only | createdDate | 3 | 78 | 49631 | 0.0107 | 0.0823 | 0.0183 | 0.3526 | 0.3654 |
| march_april | createdDate | 3,4 | 93 | 134355 | 0.0185 | 0.1070 | 0.0164 | 0.1797 | 0.5233 |
| march_april_may | createdDate | 3,4,5 | 97 | 232307 | 0.0102 | 0.1176 | 0.0108 | 0.0545 | 0.6308 |