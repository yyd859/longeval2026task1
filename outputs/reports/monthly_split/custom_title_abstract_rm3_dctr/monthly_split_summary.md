# Snapshot-1 Month Split Evaluation

| Split | Date Field | Months | Queries | Docs | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| march_only | createdDate | 3 | 78 | 49631 | 0.1817 | 0.1996 | 0.1654 | 0.3034 | 0.3034 |
| march_april | createdDate | 3,4 | 93 | 134355 | 0.2365 | 0.2721 | 0.2085 | 0.4585 | 0.4648 |
| march_april_may | createdDate | 3,4,5 | 97 | 232307 | 0.2798 | 0.3282 | 0.2377 | 0.5347 | 0.5654 |