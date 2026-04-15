# Snapshot-1 Month Split Evaluation

| Split | Date Field | Months | Queries | Docs | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| march_only | updatedDate | 3 | 86 | 48183 | 0.1912 | 0.2161 | 0.1714 | 0.3508 | 0.3508 |
| march_april | updatedDate | 3,4 | 95 | 100241 | 0.2429 | 0.2892 | 0.2140 | 0.4953 | 0.5077 |
| march_april_may | updatedDate | 3,4,5 | 100 | 200527 | 0.2534 | 0.3312 | 0.2278 | 0.5922 | 0.6348 |