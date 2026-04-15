# Snapshot-1 Month Split Evaluation

| Split | Date Field | Months | Queries | Docs | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| march_only | updatedDate | 3 | 86 | 48183 | 0.0089 | 0.0749 | 0.0141 | 0.3508 | 0.3508 |
| march_april | updatedDate | 3,4 | 95 | 100241 | 0.0234 | 0.1108 | 0.0255 | 0.3836 | 0.5025 |
| march_april_may | updatedDate | 3,4,5 | 100 | 200527 | 0.0171 | 0.1249 | 0.0171 | 0.0648 | 0.6377 |