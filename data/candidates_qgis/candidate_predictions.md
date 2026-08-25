# Predictions ResNet RGB + LiDAR - candidats inconnus

Seuil de decision : `0.45`

| Candidat | Patch | Type | P(archeologique) | Prediction | Priorite | Compatibilite |
|---|---|---|---:|---|---|---|
| candidat04 | candidat04_tres_large | tres_large | 0.204 | non_archeologique | faible | context_only |
| candidat04 | candidat04_patch | patch | 0.091 | non_archeologique | faible | comparable |
| candidat03 | candidat03_patch | patch | 0.091 | non_archeologique | faible | comparable |
| candidat01 | candidat01_patch | patch | 0.077 | non_archeologique | faible | comparable |
| candidat01 | candidat01_large | large | 0.068 | non_archeologique | faible | comparable |
| candidat03 | candidat03_tres_large | tres_large | 0.067 | non_archeologique | faible | context_only |
| candidat01 | candidat01_tres_large | tres_large | 0.061 | non_archeologique | faible | context_only |
| candidat04 | candidat04_large | large | 0.053 | non_archeologique | faible | comparable |
| candidat03 | candidat03_large | large | 0.042 | non_archeologique | faible | comparable |
| candidat02 | candidat02_tres_large | tres_large | 0.013 | non_archeologique | faible | context_only |
| candidat02 | candidat02_patch | patch | 0.005 | non_archeologique | faible | comparable |
| candidat02 | candidat02_large | large | 0.005 | non_archeologique | faible | comparable |

## Synthese par candidat

- `candidat01` : moyenne patch+large = 0.072, maximum = 0.077
- `candidat02` : moyenne patch+large = 0.005, maximum = 0.005
- `candidat03` : moyenne patch+large = 0.066, maximum = 0.091
- `candidat04` : moyenne patch+large = 0.072, maximum = 0.091

> Ces scores servent a prioriser une verification humaine. Ils ne constituent pas une preuve archeologique.
