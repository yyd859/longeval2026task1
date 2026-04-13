# Snapshot-1 Month Split Evaluation

| Split | Date Field | Months | Queries | Docs | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| march_only | updatedDate | 3 | 86 | 48183 | 0.2874 | 0.3126 | 0.2704 | 0.4477 | 0.4477 |
| march_april | updatedDate | 3,4 | 95 | 100241 | 0.3220 | 0.3599 | 0.2813 | 0.5623 | 0.5706 |
| march_april_may | updatedDate | 3,4,5 | 100 | 200527 | 0.3589 | 0.4368 | 0.3203 | 0.6634 | 0.7260 |