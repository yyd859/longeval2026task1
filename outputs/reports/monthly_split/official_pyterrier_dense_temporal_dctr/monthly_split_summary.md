# Snapshot-1 Month Split Evaluation

| Split | Date Field | Months | Queries | Docs | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| march_only | updatedDate | 3 | 86 | 48183 | 0.2088 | 0.2349 | 0.1973 | 0.3643 | 0.3643 |
| march_april | updatedDate | 3,4 | 95 | 100241 | 0.2776 | 0.3114 | 0.2455 | 0.4583 | 0.4934 |
| march_april_may | updatedDate | 3,4,5 | 100 | 200527 | 0.2938 | 0.3578 | 0.2627 | 0.5179 | 0.6267 |