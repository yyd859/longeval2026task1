# Snapshot-1 Month Split Evaluation

| Split | Date Field | Months | Queries | Docs | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| march_only | updatedDate | 3 | 86 | 48183 | 0.2320 | 0.2430 | 0.2047 | 0.3508 | 0.3508 |
| march_april | updatedDate | 3,4 | 95 | 100241 | 0.2533 | 0.2977 | 0.2199 | 0.5062 | 0.5077 |
| march_april_may | updatedDate | 3,4,5 | 100 | 200527 | 0.3235 | 0.3867 | 0.2863 | 0.6155 | 0.6348 |