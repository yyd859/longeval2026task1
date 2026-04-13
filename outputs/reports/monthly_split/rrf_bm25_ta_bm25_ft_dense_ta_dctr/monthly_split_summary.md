# Snapshot-1 Month Split Evaluation

| Split | Date Field | Months | Queries | Docs | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| march_only | updatedDate | 3 | 86 | 48183 | 0.2666 | 0.2874 | 0.2371 | 0.4419 | 0.4419 |
| march_april | updatedDate | 3,4 | 95 | 100241 | 0.3136 | 0.3597 | 0.2750 | 0.5703 | 0.5844 |
| march_april_may | updatedDate | 3,4,5 | 100 | 200527 | 0.3170 | 0.4069 | 0.2727 | 0.6928 | 0.7392 |