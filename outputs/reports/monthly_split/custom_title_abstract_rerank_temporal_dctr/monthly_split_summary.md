# Snapshot-1 Month Split Evaluation

| Split | Date Field | Months | Queries | Docs | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| march_only | updatedDate | 3 | 86 | 48183 | 0.1864 | 0.2114 | 0.1655 | 0.3508 | 0.3508 |
| march_april | updatedDate | 3,4 | 95 | 100241 | 0.2340 | 0.2805 | 0.2031 | 0.4953 | 0.5077 |
| march_april_may | updatedDate | 3,4,5 | 100 | 200527 | 0.2489 | 0.3268 | 0.2252 | 0.5922 | 0.6348 |