# Snapshot-1 Month Split Evaluation

| Split | Date Field | Months | Queries | Docs | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| march_only | publishedDate | 3 | 74 | 173031 | 0.2241 | 0.2500 | 0.2005 | 0.3333 | 0.4167 |
| march_april | publishedDate | 3,4 | 92 | 343421 | 0.2792 | 0.3093 | 0.2362 | 0.3812 | 0.5399 |
| march_april_may | publishedDate | 3,4,5 | 96 | 525293 | 0.2917 | 0.3484 | 0.2502 | 0.4679 | 0.6013 |