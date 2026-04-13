# Snapshot-1 Month Split Evaluation

| Split | Date Field | Months | Queries | Docs | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| march_only | updatedDate | 3 | 86 | 48183 | 0.2041 | 0.2267 | 0.1701 | 0.4031 | 0.4031 |
| march_april | updatedDate | 3,4 | 95 | 100241 | 0.2534 | 0.2972 | 0.2099 | 0.5255 | 0.5376 |
| march_april_may | updatedDate | 3,4,5 | 100 | 200527 | 0.2630 | 0.3476 | 0.2177 | 0.6176 | 0.6800 |