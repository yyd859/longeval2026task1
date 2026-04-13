# Snapshot-1 Month Split Evaluation

| Split | Date Field | Months | Queries | Docs | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| march_only | updatedDate | 3 | 86 | 48183 | 0.1961 | 0.2141 | 0.1687 | 0.3508 | 0.3508 |
| march_april | updatedDate | 3,4 | 95 | 100241 | 0.2357 | 0.2754 | 0.1970 | 0.4983 | 0.5025 |
| march_april_may | updatedDate | 3,4,5 | 100 | 200527 | 0.2822 | 0.3617 | 0.2606 | 0.6068 | 0.6377 |