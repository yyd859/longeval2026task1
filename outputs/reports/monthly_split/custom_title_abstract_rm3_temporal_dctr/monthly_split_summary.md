# Snapshot-1 Month Split Evaluation

| Split | Date Field | Months | Queries | Docs | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| march_only | createdDate | 3 | 78 | 49631 | 0.0111 | 0.0659 | 0.0139 | 0.3034 | 0.3034 |
| march_april | createdDate | 3,4 | 93 | 134355 | 0.0038 | 0.0849 | 0.0091 | 0.0965 | 0.4648 |
| march_april_may | createdDate | 3,4,5 | 97 | 232307 | 0.0103 | 0.1073 | 0.0172 | 0.0811 | 0.5654 |