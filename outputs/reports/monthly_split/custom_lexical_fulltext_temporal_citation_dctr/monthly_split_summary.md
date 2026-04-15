# Snapshot-1 Month Split Evaluation

| Split | Date Field | Months | Queries | Docs | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| march_only | updatedDate | 3 | 86 | 48183 | 0.0197 | 0.1048 | 0.0289 | 0.4360 | 0.4477 |
| march_april | updatedDate | 3,4 | 95 | 100241 | 0.0197 | 0.1173 | 0.0178 | 0.3029 | 0.5706 |
| march_april_may | updatedDate | 3,4,5 | 100 | 200527 | 0.0135 | 0.1382 | 0.0131 | 0.0707 | 0.7260 |