# Snapshot-1 Month Split Evaluation

| Split | Date Field | Months | Queries | Docs | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| march_only | updatedDate | 3 | 86 | 48183 | 0.2728 | 0.2881 | 0.2426 | 0.4302 | 0.4302 |
| march_april | updatedDate | 3,4 | 95 | 100241 | 0.3246 | 0.3619 | 0.2839 | 0.5603 | 0.5671 |
| march_april_may | updatedDate | 3,4,5 | 100 | 200527 | 0.3368 | 0.4135 | 0.2874 | 0.6944 | 0.7164 |