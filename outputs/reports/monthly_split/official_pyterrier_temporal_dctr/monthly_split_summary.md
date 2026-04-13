# Snapshot-1 Month Split Evaluation

| Split | Date Field | Months | Queries | Docs | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| march_only | updatedDate | 3 | 86 | 48183 | 0.0103 | 0.0754 | 0.0149 | 0.3508 | 0.3508 |
| march_april | updatedDate | 3,4 | 95 | 100241 | 0.0149 | 0.1075 | 0.0198 | 0.3198 | 0.5077 |
| march_april_may | updatedDate | 3,4,5 | 100 | 200527 | 0.0132 | 0.1253 | 0.0162 | 0.1089 | 0.6348 |