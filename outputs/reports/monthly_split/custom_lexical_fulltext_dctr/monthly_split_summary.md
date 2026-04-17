# Snapshot-1 Month Split Evaluation

| Split | Date Field | Months | Queries | Docs | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| march_only | createdDate | 3 | 78 | 49631 | 0.2366 | 0.2495 | 0.2085 | 0.3654 | 0.3654 |
| march_april | createdDate | 3,4 | 93 | 134355 | 0.2457 | 0.2874 | 0.2044 | 0.5036 | 0.5233 |
| march_april_may | createdDate | 3,4,5 | 97 | 232307 | 0.2775 | 0.3543 | 0.2439 | 0.5932 | 0.6308 |