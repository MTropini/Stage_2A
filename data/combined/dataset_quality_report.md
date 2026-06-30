# Dataset quality report

## Global summary

- Sites: 15
- Training-usable samples: 292
- Unusable samples: 2
- Excluded patch types: tres_large
- Target per site: 4 archaeological patches, 1 large patch, 8 negatives

## Counts

- Labels: archeologique=106, non_archeologique=186
- Patch types: large=28, neg=186, patch=78
- Sources: exports_qgis=173, exports_qgis_auto=119

## Sites needing action

| Site | Usable | Patch | Large | Negative | Unusable | Recommendation |
|---|---:|---:|---:|---:|---:|---|
| site13 | 21 | 3 | 2 | 16 | 0 | add_1_archaeological_patch |
| site15 | 17 | 4 | 1 | 12 | 2 | fix_2_file_issue |

## Per-site detail

| Site | Arch. total | Neg. total | Patch | Large | Sources | File issues |
|---|---:|---:|---:|---:|---|---|
| site01 | 8 | 12 | 6 | 2 | exports_qgis:12;exports_qgis_auto:8 |  |
| site02 | 7 | 12 | 5 | 2 | exports_qgis:12;exports_qgis_auto:7 |  |
| site03 | 6 | 12 | 4 | 2 | exports_qgis:10;exports_qgis_auto:8 |  |
| site04 | 9 | 12 | 7 | 2 | exports_qgis:13;exports_qgis_auto:8 |  |
| site05 | 9 | 11 | 7 | 2 | exports_qgis:12;exports_qgis_auto:8 |  |
| site06 | 6 | 12 | 4 | 2 | exports_qgis:10;exports_qgis_auto:8 |  |
| site07 | 7 | 11 | 5 | 2 | exports_qgis:10;exports_qgis_auto:8 |  |
| site08 | 7 | 11 | 5 | 2 | exports_qgis:10;exports_qgis_auto:8 |  |
| site09 | 6 | 12 | 5 | 1 | exports_qgis:10;exports_qgis_auto:8 |  |
| site10 | 7 | 11 | 5 | 2 | exports_qgis:10;exports_qgis_auto:8 |  |
| site11 | 8 | 12 | 6 | 2 | exports_qgis:12;exports_qgis_auto:8 |  |
| site12 | 8 | 17 | 6 | 2 | exports_qgis:17;exports_qgis_auto:8 |  |
| site13 | 5 | 16 | 3 | 2 | exports_qgis:13;exports_qgis_auto:8 |  |
| site14 | 8 | 13 | 6 | 2 | exports_qgis:13;exports_qgis_auto:8 |  |
| site15 | 5 | 12 | 4 | 1 | exports_qgis:9;exports_qgis_auto:8 | site15_neg01=size_mismatch;site15_neg02=size_mismatch |
