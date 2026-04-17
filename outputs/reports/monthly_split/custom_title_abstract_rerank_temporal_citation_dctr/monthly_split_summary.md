# Snapshot-1 Month Split Evaluation

| Split | Date Field | Months | Queries | Docs | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| march_only | createdDate | 3 | 78 | 49631 | 0.1896 | 0.2025 | 0.1709 | 0.2906 | 0.2906 |
| march_april | createdDate | 3,4 | 93 | 134355 | 0.2416 | 0.2790 | 0.2195 | 0.4589 | 0.4643 |
| march_april_may | createdDate | 3,4,5 | 97 | 232307 | 0.2410 | 0.3022 | 0.2174 | 0.5285 | 0.5552 |