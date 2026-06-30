# RGB + LiDAR fusion error report

## Summary

- Samples: 292
- Correct: 226
- False negatives: 41
- False positives: 25
- Excluded patch types: tres_large

## Errors By Site

| Site | False negatives | False positives |
|---|---:|---:|
| site01 | 3 | 5 |
| site02 | 1 | 10 |
| site03 | 4 | 0 |
| site04 | 2 | 1 |
| site05 | 1 | 0 |
| site06 | 4 | 0 |
| site07 | 2 | 0 |
| site08 | 4 | 1 |
| site09 | 6 | 1 |
| site10 | 1 | 0 |
| site11 | 1 | 0 |
| site12 | 7 | 3 |
| site13 | 1 | 1 |
| site14 | 1 | 3 |
| site15 | 3 | 0 |

## High-Confidence False Negatives

| Patch | Site | Type | P(arch.) | RGB | LiDAR |
|---|---|---|---:|---|---|
| site09_patch02 | site09 | patch | 0.000 | data/exports_qgis/rgb/site09_patch02.png | data/exports_qgis/lidar/site09_patch02_lidar.png |
| site09_patch | site09 | patch | 0.000 | data/exports_qgis_auto/rgb/site09_patch.png | data/exports_qgis_auto/lidar/site09_patch_lidar.png |
| site03_patch04 | site03 | patch | 0.001 | data/exports_qgis/rgb/site03_patch04.png | data/exports_qgis/lidar/site03_patch04_lidar.png |
| site03_patch | site03 | patch | 0.001 | data/exports_qgis_auto/rgb/site03_patch.png | data/exports_qgis_auto/lidar/site03_patch_lidar.png |
| site12_patch03 | site12 | patch | 0.001 | data/exports_qgis/rgb/site12_patch03.png | data/exports_qgis/lidar/site12_patch03_lidar.png |
| site10_large | site10 | large | 0.001 | data/exports_qgis_auto/rgb/site10_large.png | data/exports_qgis_auto/lidar/site10_large_lidar.png |
| site02_patch04 | site02 | patch | 0.002 | data/exports_qgis/rgb/site02_patch04.png | data/exports_qgis/lidar/site02_patch04_lidar.png |
| site03_large | site03 | large | 0.002 | data/exports_qgis/rgb/site03_large.png | data/exports_qgis/lidar/site03_large_lidar.png |
| site09_patch04 | site09 | patch | 0.004 | data/exports_qgis/rgb/site09_patch04.png | data/exports_qgis/lidar/site09_patch04_lidar.png |
| site06_large | site06 | large | 0.004 | data/exports_qgis_auto/rgb/site06_large.png | data/exports_qgis_auto/lidar/site06_large_lidar.png |
| site03_large | site03 | large | 0.005 | data/exports_qgis_auto/rgb/site03_large.png | data/exports_qgis_auto/lidar/site03_large_lidar.png |
| site12_patch04 | site12 | patch | 0.007 | data/exports_qgis/rgb/site12_patch04.png | data/exports_qgis/lidar/site12_patch04_lidar.png |
| site11_large | site11 | large | 0.009 | data/exports_qgis_auto/rgb/site11_large.png | data/exports_qgis_auto/lidar/site11_large_lidar.png |
| site09_patch03 | site09 | patch | 0.012 | data/exports_qgis/rgb/site09_patch03.png | data/exports_qgis/lidar/site09_patch03_lidar.png |
| site06_large | site06 | large | 0.013 | data/exports_qgis/rgb/site06_large.png | data/exports_qgis/lidar/site06_large_lidar.png |
| site15_large | site15 | large | 0.014 | data/exports_qgis_auto/rgb/site15_large.png | data/exports_qgis_auto/lidar/site15_large_lidar.png |
| site12_large | site12 | large | 0.019 | data/exports_qgis/rgb/site12_large.png | data/exports_qgis/lidar/site12_large_lidar.png |
| site04_patch02 | site04 | patch | 0.032 | data/exports_qgis/rgb/site04_patch02.png | data/exports_qgis/lidar/site04_patch02_lidar.png |
| site06_patch | site06 | patch | 0.034 | data/exports_qgis_auto/rgb/site06_patch.png | data/exports_qgis_auto/lidar/site06_patch_lidar.png |
| site05_large | site05 | large | 0.036 | data/exports_qgis_auto/rgb/site05_large.png | data/exports_qgis_auto/lidar/site05_large_lidar.png |
| site12_patch02 | site12 | patch | 0.057 | data/exports_qgis/rgb/site12_patch02.png | data/exports_qgis/lidar/site12_patch02_lidar.png |
| site07_patch02 | site07 | patch | 0.065 | data/exports_qgis/rgb/site07_patch02.png | data/exports_qgis/lidar/site07_patch02_lidar.png |
| site14_patch04 | site14 | patch | 0.075 | data/exports_qgis/rgb/site14_patch04.png | data/exports_qgis/lidar/site14_patch04_lidar.png |
| site12_patch | site12 | patch | 0.099 | data/exports_qgis_auto/rgb/site12_patch.png | data/exports_qgis_auto/lidar/site12_patch_lidar.png |
| site08_patch04 | site08 | patch | 0.100 | data/exports_qgis/rgb/site08_patch04.png | data/exports_qgis/lidar/site08_patch04_lidar.png |

## High-Confidence False Positives

| Patch | Site | Type | P(arch.) | RGB | LiDAR |
|---|---|---|---:|---|---|
| site12_neg_auto03 | site12 | neg | 1.000 | data/exports_qgis_auto/rgb/site12_neg_auto03.png | data/exports_qgis_auto/lidar/site12_neg_auto03_lidar.png |
| site01_neg_auto03 | site01 | neg | 1.000 | data/exports_qgis_auto/rgb/site01_neg_auto03.png | data/exports_qgis_auto/lidar/site01_neg_auto03_lidar.png |
| site02_neg02 | site02 | neg | 1.000 | data/exports_qgis/rgb/site02_neg02.png | data/exports_qgis/lidar/site02_neg02_lidar.png |
| site12_neg11 | site12 | neg | 0.999 | data/exports_qgis/rgb/site12_neg11.png | data/exports_qgis/lidar/site12_neg11_lidar.png |
| site02_neg06 | site02 | neg | 0.999 | data/exports_qgis/rgb/site02_neg06.png | data/exports_qgis/lidar/site02_neg06_lidar.png |
| site02_neg01 | site02 | neg | 0.998 | data/exports_qgis/rgb/site02_neg01.png | data/exports_qgis/lidar/site02_neg01_lidar.png |
| site02_neg03 | site02 | neg | 0.997 | data/exports_qgis/rgb/site02_neg03.png | data/exports_qgis/lidar/site02_neg03_lidar.png |
| site02_neg_auto05 | site02 | neg | 0.994 | data/exports_qgis_auto/rgb/site02_neg_auto05.png | data/exports_qgis_auto/lidar/site02_neg_auto05_lidar.png |
| site01_neg_auto05 | site01 | neg | 0.992 | data/exports_qgis_auto/rgb/site01_neg_auto05.png | data/exports_qgis_auto/lidar/site01_neg_auto05_lidar.png |
| site02_neg05 | site02 | neg | 0.990 | data/exports_qgis/rgb/site02_neg05.png | data/exports_qgis/lidar/site02_neg05_lidar.png |
| site02_neg_auto03 | site02 | neg | 0.983 | data/exports_qgis_auto/rgb/site02_neg_auto03.png | data/exports_qgis_auto/lidar/site02_neg_auto03_lidar.png |
| site09_neg06 | site09 | neg | 0.968 | data/exports_qgis/rgb/site09_neg06.png | data/exports_qgis/lidar/site09_neg06_lidar.png |
| site14_neg07 | site14 | neg | 0.952 | data/exports_qgis/rgb/site14_neg07.png | data/exports_qgis/lidar/site14_neg07_lidar.png |
| site01_neg03 | site01 | neg | 0.901 | data/exports_qgis/rgb/site01_neg03.png | data/exports_qgis/lidar/site01_neg03_lidar.png |
| site12_neg10 | site12 | neg | 0.821 | data/exports_qgis/rgb/site12_neg10.png | data/exports_qgis/lidar/site12_neg10_lidar.png |
| site01_neg05 | site01 | neg | 0.820 | data/exports_qgis/rgb/site01_neg05.png | data/exports_qgis/lidar/site01_neg05_lidar.png |
| site02_neg07 | site02 | neg | 0.805 | data/exports_qgis/rgb/site02_neg07.png | data/exports_qgis/lidar/site02_neg07_lidar.png |
| site02_neg_auto06 | site02 | neg | 0.798 | data/exports_qgis_auto/rgb/site02_neg_auto06.png | data/exports_qgis_auto/lidar/site02_neg_auto06_lidar.png |
| site14_neg06 | site14 | neg | 0.794 | data/exports_qgis/rgb/site14_neg06.png | data/exports_qgis/lidar/site14_neg06_lidar.png |
| site02_neg_auto01 | site02 | neg | 0.783 | data/exports_qgis_auto/rgb/site02_neg_auto01.png | data/exports_qgis_auto/lidar/site02_neg_auto01_lidar.png |
| site08_neg05 | site08 | neg | 0.764 | data/exports_qgis/rgb/site08_neg05.png | data/exports_qgis/lidar/site08_neg05_lidar.png |
| site04_neg06 | site04 | neg | 0.758 | data/exports_qgis/rgb/site04_neg06.png | data/exports_qgis/lidar/site04_neg06_lidar.png |
| site14_neg_auto06 | site14 | neg | 0.715 | data/exports_qgis_auto/rgb/site14_neg_auto06.png | data/exports_qgis_auto/lidar/site14_neg_auto06_lidar.png |
| site13_neg10 | site13 | neg | 0.649 | data/exports_qgis/rgb/site13_neg10.png | data/exports_qgis/lidar/site13_neg10_lidar.png |
| site01_neg_auto01 | site01 | neg | 0.504 | data/exports_qgis_auto/rgb/site01_neg_auto01.png | data/exports_qgis_auto/lidar/site01_neg_auto01_lidar.png |

## Error Counts By Patch Type

| Patch type | False negatives | False positives |
|---|---:|---:|
| large | 13 | 0 |
| neg | 0 | 25 |
| patch | 28 | 0 |
