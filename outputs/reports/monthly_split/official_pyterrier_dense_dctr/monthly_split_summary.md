# Snapshot-1 Month Split Evaluation

| Split | Date Field | Months | Queries | Docs | nDCG@10 | nDCG@1000 | MAP | Recall@100 | Recall@1000 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| march_only | publishedDate | 3 | 74 | 173031 | 0.2009 | 0.2369 | 0.1769 | 0.4099 | 0.4167 |
| march_april | publishedDate | 3,4 | 92 | 343421 | 0.2182 | 0.2740 | 0.1863 | 0.5101 | 0.5399 |
| march_april_may | publishedDate | 3,4,5 | 96 | 525293 | 0.2316 | 0.3060 | 0.1943 | 0.5349 | 0.6013 |