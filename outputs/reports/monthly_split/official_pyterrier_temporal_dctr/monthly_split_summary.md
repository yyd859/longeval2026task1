# Snapshot-1 Month Split Evaluation

| Split | Date Field | Months | Queries | Docs | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| march_only | createdDate | 3 | 78 | 49631 | 0.0015 | 0.0596 | 0.0101 | 0.2906 | 0.2906 |
| march_april | createdDate | 3,4 | 93 | 134355 | 0.0067 | 0.0871 | 0.0118 | 0.1048 | 0.4643 |
| march_april_may | createdDate | 3,4,5 | 97 | 232307 | 0.0076 | 0.0992 | 0.0099 | 0.0716 | 0.5552 |