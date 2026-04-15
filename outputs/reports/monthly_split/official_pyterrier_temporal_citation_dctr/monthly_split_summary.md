# Snapshot-1 Month Split Evaluation

| Split | Date Field | Months | Queries | Docs | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| march_only | updatedDate | 3 | 86 | 48183 | 0.0139 | 0.0779 | 0.0183 | 0.3508 | 0.3508 |
| march_april | updatedDate | 3,4 | 95 | 100241 | 0.0158 | 0.1090 | 0.0218 | 0.3198 | 0.5077 |
| march_april_may | updatedDate | 3,4,5 | 100 | 200527 | 0.0137 | 0.1255 | 0.0166 | 0.1089 | 0.6348 |