# Snapshot-1 Month Split Evaluation

| Split | Date Field | Months | Queries | Docs | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| march_only | updatedDate | 3 | 86 | 48183 | 0.2074 | 0.2340 | 0.1949 | 0.3643 | 0.3643 |
| march_april | updatedDate | 3,4 | 95 | 100241 | 0.2714 | 0.3052 | 0.2385 | 0.4609 | 0.4934 |
| march_april_may | updatedDate | 3,4,5 | 100 | 200527 | 0.2861 | 0.3498 | 0.2539 | 0.5179 | 0.6267 |