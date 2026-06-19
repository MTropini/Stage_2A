# Dataset quality report

## Global summary

- Sites: 15
- Training-usable samples: 229
- Unusable samples: 2
- Excluded patch types: tres_large
- Target per site: 4 archaeological patches, 1 large patch, 8 negatives

## Counts

- Labels: archeologique=92, non_archeologique=137
- Patch types: large=28, neg=137, patch=64
- Sources: exports_qgis=110, exports_qgis_auto=119

## Sites needing action

| Site | Usable | Patch | Large | Negative | Unusable | Recommendation |
|---|---:|---:|---:|---:|---:|---|
| site07 | 13 | 3 | 2 | 8 | 0 | add_1_archaeological_patch |
| site08 | 14 | 3 | 2 | 9 | 0 | add_1_archaeological_patch |
| site09 | 12 | 5 | 1 | 6 | 0 | add_2_negative |
| site10 | 13 | 3 | 2 | 8 | 0 | add_1_archaeological_patch |
| site11 | 11 | 3 | 2 | 6 | 0 | add_1_archaeological_patch;add_2_negative |
| site12 | 13 | 3 | 2 | 8 | 0 | add_1_archaeological_patch |
| site13 | 12 | 3 | 2 | 7 | 0 | add_1_archaeological_patch;add_1_negative |
| site14 | 13 | 4 | 2 | 7 | 0 | add_1_negative |
| site15 | 12 | 4 | 1 | 7 | 2 | add_1_negative;fix_2_file_issue |

## Per-site detail

| Site | Arch. total | Neg. total | Patch | Large | Sources | File issues |
|---|---:|---:|---:|---:|---|---|
| site01 | 8 | 12 | 6 | 2 | exports_qgis:12;exports_qgis_auto:8 |  |
| site02 | 7 | 12 | 5 | 2 | exports_qgis:12;exports_qgis_auto:7 |  |
| site03 | 6 | 12 | 4 | 2 | exports_qgis:10;exports_qgis_auto:8 |  |
| site04 | 9 | 12 | 7 | 2 | exports_qgis:13;exports_qgis_auto:8 |  |
| site05 | 9 | 11 | 7 | 2 | exports_qgis:12;exports_qgis_auto:8 |  |
| site06 | 6 | 12 | 4 | 2 | exports_qgis:10;exports_qgis_auto:8 |  |
| site07 | 5 | 8 | 3 | 2 | exports_qgis:5;exports_qgis_auto:8 |  |
| site08 | 5 | 9 | 3 | 2 | exports_qgis:6;exports_qgis_auto:8 |  |
| site09 | 6 | 6 | 5 | 1 | exports_qgis:4;exports_qgis_auto:8 |  |
| site10 | 5 | 8 | 3 | 2 | exports_qgis:5;exports_qgis_auto:8 |  |
| site11 | 5 | 6 | 3 | 2 | exports_qgis:3;exports_qgis_auto:8 |  |
| site12 | 5 | 8 | 3 | 2 | exports_qgis:5;exports_qgis_auto:8 |  |
| site13 | 5 | 7 | 3 | 2 | exports_qgis:4;exports_qgis_auto:8 |  |
| site14 | 6 | 7 | 4 | 2 | exports_qgis:5;exports_qgis_auto:8 |  |
| site15 | 5 | 7 | 4 | 1 | exports_qgis:4;exports_qgis_auto:8 | site15_neg01=size_mismatch;site15_neg02=size_mismatch |
