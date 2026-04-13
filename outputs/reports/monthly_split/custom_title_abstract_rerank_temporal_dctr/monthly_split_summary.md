# Snapshot-1 Month Split Evaluation

| Split | Date Field | Months | Queries | Docs | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| march_only | updatedDate | 3 | 86 | 48183 | 0.2307 | 0.2325 | 0.1950 | 0.3275 | 0.3275 |
| march_april | updatedDate | 3,4 | 95 | 100241 | 0.2678 | 0.2840 | 0.2270 | 0.4160 | 0.4160 |
| march_april_may | updatedDate | 3,4,5 | 100 | 200527 | 0.3052 | 0.3471 | 0.2634 | 0.5509 | 0.5509 |