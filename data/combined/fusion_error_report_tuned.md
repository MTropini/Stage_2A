# RGB + LiDAR fusion error report

## Summary

- Samples: 292
- Correct: 234
- False negatives: 36
- False positives: 22
- Excluded patch types: tres_large

## Errors By Site

| Site | False negatives | False positives |
|---|---:|---:|
| site01 | 1 | 4 |
| site02 | 1 | 10 |
| site03 | 4 | 0 |
| site04 | 2 | 1 |
| site05 | 1 | 0 |
| site06 | 5 | 0 |
| site07 | 1 | 1 |
| site08 | 5 | 0 |
| site09 | 5 | 0 |
| site10 | 1 | 0 |
| site11 | 1 | 0 |
| site12 | 4 | 4 |
| site13 | 0 | 1 |
| site14 | 0 | 1 |
| site15 | 5 | 0 |

## High-Confidence False Negatives

| Patch | Site | Type | P(arch.) | RGB | LiDAR |
|---|---|---|---:|---|---|
| site09_patch | site09 | patch | 0.014 | data/exports_qgis_auto/rgb/site09_patch.png | data/exports_qgis_auto/lidar/site09_patch_lidar.png |
| site09_patch02 | site09 | patch | 0.016 | data/exports_qgis/rgb/site09_patch02.png | data/exports_qgis/lidar/site09_patch02_lidar.png |
| site03_patch | site03 | patch | 0.017 | data/exports_qgis_auto/rgb/site03_patch.png | data/exports_qgis_auto/lidar/site03_patch_lidar.png |
| site03_large | site03 | large | 0.018 | data/exports_qgis/rgb/site03_large.png | data/exports_qgis/lidar/site03_large_lidar.png |
| site03_patch04 | site03 | patch | 0.041 | data/exports_qgis/rgb/site03_patch04.png | data/exports_qgis/lidar/site03_patch04_lidar.png |
| site06_large | site06 | large | 0.042 | data/exports_qgis_auto/rgb/site06_large.png | data/exports_qgis_auto/lidar/site06_large_lidar.png |
| site03_large | site03 | large | 0.050 | data/exports_qgis_auto/rgb/site03_large.png | data/exports_qgis_auto/lidar/site03_large_lidar.png |
| site10_large | site10 | large | 0.064 | data/exports_qgis_auto/rgb/site10_large.png | data/exports_qgis_auto/lidar/site10_large_lidar.png |
| site12_patch03 | site12 | patch | 0.081 | data/exports_qgis/rgb/site12_patch03.png | data/exports_qgis/lidar/site12_patch03_lidar.png |
| site05_large | site05 | large | 0.108 | data/exports_qgis_auto/rgb/site05_large.png | data/exports_qgis_auto/lidar/site05_large_lidar.png |
| site15_patch | site15 | patch | 0.112 | data/exports_qgis_auto/rgb/site15_patch.png | data/exports_qgis_auto/lidar/site15_patch_lidar.png |
| site02_patch04 | site02 | patch | 0.124 | data/exports_qgis/rgb/site02_patch04.png | data/exports_qgis/lidar/site02_patch04_lidar.png |
| site15_large | site15 | large | 0.133 | data/exports_qgis_auto/rgb/site15_large.png | data/exports_qgis_auto/lidar/site15_large_lidar.png |
| site09_patch04 | site09 | patch | 0.147 | data/exports_qgis/rgb/site09_patch04.png | data/exports_qgis/lidar/site09_patch04_lidar.png |
| site11_large | site11 | large | 0.168 | data/exports_qgis_auto/rgb/site11_large.png | data/exports_qgis_auto/lidar/site11_large_lidar.png |
| site15_patch03 | site15 | patch | 0.168 | data/exports_qgis/rgb/site15_patch03.png | data/exports_qgis/lidar/site15_patch03_lidar.png |
| site15_patch02 | site15 | patch | 0.171 | data/exports_qgis/rgb/site15_patch02.png | data/exports_qgis/lidar/site15_patch02_lidar.png |
| site09_patch03 | site09 | patch | 0.176 | data/exports_qgis/rgb/site09_patch03.png | data/exports_qgis/lidar/site09_patch03_lidar.png |
| site06_large | site06 | large | 0.179 | data/exports_qgis/rgb/site06_large.png | data/exports_qgis/lidar/site06_large_lidar.png |
| site15_patch01 | site15 | patch | 0.197 | data/exports_qgis/rgb/site15_patch01.png | data/exports_qgis/lidar/site15_patch01_lidar.png |
| site06_patch | site06 | patch | 0.214 | data/exports_qgis_auto/rgb/site06_patch.png | data/exports_qgis_auto/lidar/site06_patch_lidar.png |
| site06_patch02 | site06 | patch | 0.214 | data/exports_qgis/rgb/site06_patch02.png | data/exports_qgis/lidar/site06_patch02_lidar.png |
| site08_patch04 | site08 | patch | 0.229 | data/exports_qgis/rgb/site08_patch04.png | data/exports_qgis/lidar/site08_patch04_lidar.png |
| site12_patch04 | site12 | patch | 0.229 | data/exports_qgis/rgb/site12_patch04.png | data/exports_qgis/lidar/site12_patch04_lidar.png |
| site12_patch02 | site12 | patch | 0.245 | data/exports_qgis/rgb/site12_patch02.png | data/exports_qgis/lidar/site12_patch02_lidar.png |

## High-Confidence False Positives

| Patch | Site | Type | P(arch.) | RGB | LiDAR |
|---|---|---|---:|---|---|
| site02_neg_auto05 | site02 | neg | 0.955 | data/exports_qgis_auto/rgb/site02_neg_auto05.png | data/exports_qgis_auto/lidar/site02_neg_auto05_lidar.png |
| site12_neg11 | site12 | neg | 0.935 | data/exports_qgis/rgb/site12_neg11.png | data/exports_qgis/lidar/site12_neg11_lidar.png |
| site02_neg02 | site02 | neg | 0.935 | data/exports_qgis/rgb/site02_neg02.png | data/exports_qgis/lidar/site02_neg02_lidar.png |
| site02_neg_auto03 | site02 | neg | 0.918 | data/exports_qgis_auto/rgb/site02_neg_auto03.png | data/exports_qgis_auto/lidar/site02_neg_auto03_lidar.png |
| site02_neg01 | site02 | neg | 0.899 | data/exports_qgis/rgb/site02_neg01.png | data/exports_qgis/lidar/site02_neg01_lidar.png |
| site02_neg06 | site02 | neg | 0.895 | data/exports_qgis/rgb/site02_neg06.png | data/exports_qgis/lidar/site02_neg06_lidar.png |
| site01_neg_auto03 | site01 | neg | 0.867 | data/exports_qgis_auto/rgb/site01_neg_auto03.png | data/exports_qgis_auto/lidar/site01_neg_auto03_lidar.png |
| site01_neg_auto05 | site01 | neg | 0.779 | data/exports_qgis_auto/rgb/site01_neg_auto05.png | data/exports_qgis_auto/lidar/site01_neg_auto05_lidar.png |
| site12_neg_auto03 | site12 | neg | 0.758 | data/exports_qgis_auto/rgb/site12_neg_auto03.png | data/exports_qgis_auto/lidar/site12_neg_auto03_lidar.png |
| site02_neg_auto06 | site02 | neg | 0.754 | data/exports_qgis_auto/rgb/site02_neg_auto06.png | data/exports_qgis_auto/lidar/site02_neg_auto06_lidar.png |
| site02_neg05 | site02 | neg | 0.722 | data/exports_qgis/rgb/site02_neg05.png | data/exports_qgis/lidar/site02_neg05_lidar.png |
| site02_neg03 | site02 | neg | 0.711 | data/exports_qgis/rgb/site02_neg03.png | data/exports_qgis/lidar/site02_neg03_lidar.png |
| site02_neg_auto04 | site02 | neg | 0.692 | data/exports_qgis_auto/rgb/site02_neg_auto04.png | data/exports_qgis_auto/lidar/site02_neg_auto04_lidar.png |
| site01_neg05 | site01 | neg | 0.567 | data/exports_qgis/rgb/site01_neg05.png | data/exports_qgis/lidar/site01_neg05_lidar.png |
| site04_neg06 | site04 | neg | 0.538 | data/exports_qgis/rgb/site04_neg06.png | data/exports_qgis/lidar/site04_neg06_lidar.png |
| site13_neg_auto03 | site13 | neg | 0.500 | data/exports_qgis_auto/rgb/site13_neg_auto03.png | data/exports_qgis_auto/lidar/site13_neg_auto03_lidar.png |
| site02_neg07 | site02 | neg | 0.491 | data/exports_qgis/rgb/site02_neg07.png | data/exports_qgis/lidar/site02_neg07_lidar.png |
| site12_neg10 | site12 | neg | 0.471 | data/exports_qgis/rgb/site12_neg10.png | data/exports_qgis/lidar/site12_neg10_lidar.png |
| site12_neg07 | site12 | neg | 0.468 | data/exports_qgis/rgb/site12_neg07.png | data/exports_qgis/lidar/site12_neg07_lidar.png |
| site07_neg02 | site07 | neg | 0.467 | data/exports_qgis/rgb/site07_neg02.png | data/exports_qgis/lidar/site07_neg02_lidar.png |
| site14_neg_auto06 | site14 | neg | 0.461 | data/exports_qgis_auto/rgb/site14_neg_auto06.png | data/exports_qgis_auto/lidar/site14_neg_auto06_lidar.png |
| site01_neg_auto01 | site01 | neg | 0.461 | data/exports_qgis_auto/rgb/site01_neg_auto01.png | data/exports_qgis_auto/lidar/site01_neg_auto01_lidar.png |

## Error Counts By Patch Type

| Patch type | False negatives | False positives |
|---|---:|---:|
| large | 11 | 0 |
| neg | 0 | 22 |
| patch | 25 | 0 |
