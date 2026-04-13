# Snapshot-1 Month Split Evaluation

| Split | Date Field | Months | Queries | Docs | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| march_only | updatedDate | 3 | 86 | 48183 | 0.2064 | 0.2191 | 0.1733 | 0.3508 | 0.3508 |
| march_april | updatedDate | 3,4 | 95 | 100241 | 0.2376 | 0.2764 | 0.1931 | 0.5006 | 0.5077 |
| march_april_may | updatedDate | 3,4,5 | 100 | 200527 | 0.2757 | 0.3440 | 0.2407 | 0.6044 | 0.6348 |