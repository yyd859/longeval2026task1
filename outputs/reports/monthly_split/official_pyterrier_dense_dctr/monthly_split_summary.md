# Snapshot-1 Month Split Evaluation

| Split | Date Field | Months | Queries | Docs | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| march_only | updatedDate | 3 | 86 | 48183 | 0.2188 | 0.2393 | 0.1993 | 0.3643 | 0.3643 |
| march_april | updatedDate | 3,4 | 95 | 100241 | 0.2686 | 0.3042 | 0.2366 | 0.4813 | 0.4934 |
| march_april_may | updatedDate | 3,4,5 | 100 | 200527 | 0.2719 | 0.3524 | 0.2534 | 0.5642 | 0.6267 |