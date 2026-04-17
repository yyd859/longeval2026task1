# Snapshot-1 Month Split Evaluation

| Split | Date Field | Months | Queries | Docs | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| march_only | createdDate | 3 | 78 | 49631 | 0.2546 | 0.2718 | 0.2291 | 0.3910 | 0.3910 |
| march_april | createdDate | 3,4 | 93 | 134355 | 0.2741 | 0.3122 | 0.2303 | 0.5237 | 0.5367 |
| march_april_may | createdDate | 3,4,5 | 97 | 232307 | 0.2965 | 0.3613 | 0.2450 | 0.6133 | 0.6494 |