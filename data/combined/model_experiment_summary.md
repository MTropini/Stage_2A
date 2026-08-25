# Synthese experimentale - Classification archeologique RGB + LiDAR

Date de synthese : 2026-06-30

## Objectif

L'objectif actuel est de classer des patches issus de QGIS en deux categories :

- `archeologique`
- `non_archeologique`

Le modele ne fait pas encore de detection dans une grande image. Il repond a la question suivante :

> Ce patch RGB + LiDAR ressemble-t-il a une zone archeologique ?

## Donnees utilisees

Les donnees proviennent des exports QGIS RGB et LiDAR regroupes dans le manifeste combine :

- `data/combined/dataset_audit.csv`
- `data/combined/dataset_quality_report.md`

Etat actuel du dataset d'entrainement/evaluation :

| Element | Valeur |
|---|---:|
| Sites | 15 |
| Echantillons utilisables pour l'entrainement | 292 |
| Images inutilisables | 2 |
| Images archeologiques | 106 |
| Images non archeologiques | 186 |
| Patches `patch` | 78 |
| Patches `large` | 28 |
| Patches `neg` | 186 |

Les patches `tres_large` sont exclus de l'entrainement actuel, car ils contiennent beaucoup de contexte et risquent de faire apprendre au modele l'environnement du site plutot que les formes archeologiques.

## Points dataset restants

Le dataset est globalement exploitable. Deux points restent a corriger ou surveiller :

| Site | Probleme |
|---|---|
| `site13` | Ajouter idealement 1 patch archeologique |
| `site15` | Corriger `site15_neg01` et `site15_neg02`, car les tailles RGB/LiDAR ne correspondent pas |

## Methode

Le pipeline actuel utilise une fusion RGB + LiDAR :

1. Une image RGB est envoyee dans un ResNet-18 preentraine.
2. Une image LiDAR correspondant au meme patch est envoyee dans le meme type de ResNet-18.
3. Chaque image est transformee en vecteur de 512 valeurs.
4. Les deux vecteurs sont concatenes :

```text
RGB   : 512 valeurs
LiDAR : 512 valeurs
Total : 1024 valeurs
```

5. Une regression logistique classe ensuite le vecteur fusionne en `archeologique` ou `non_archeologique`.

Le ResNet-18 n'est pas encore fine-tune. Il est utilise comme extracteur de caracteristiques visuelles.

## Validation

La validation utilise une strategie stricte :

```text
leave-one-site-out cross-validation
```

Principe :

- on entraine sur 14 sites ;
- on teste sur le site restant ;
- on repete l'operation pour chacun des 15 sites.

Cette strategie evite de tester le modele sur des images trop proches de celles qu'il a vues a l'entrainement.

## Resultats avant optimisation

Comparaison des modalites avec ResNet-18 embeddings :

| Modele | Accuracy | F1 archeologique |
|---|---:|---:|
| RGB seul | 0.714 | 0.535 |
| LiDAR seul | 0.669 | 0.455 |
| RGB + LiDAR | 0.776 | 0.626 |

Conclusion : la fusion RGB + LiDAR est la meilleure modalite parmi celles testees.

## Optimisation des hyperparametres

Une recherche d'hyperparametres a ete realisee sur :

- `scaler`
- `class_weight`
- `C`
- seuil de decision

Rapport complet :

- `data/combined/fusion_hyperparameter_search.csv`
- `data/combined/fusion_hyperparameter_search.md`

Meilleur compromis actuel :

| Parametre | Valeur |
|---|---|
| `scaler` | `none` |
| `class_weight` | `none` |
| `C` | `0.03` |
| seuil | `0.45` |

Resultat du modele optimise :

| Metrique | Valeur |
|---|---:|
| Accuracy | 0.801 |
| Precision archeologique | 0.761 |
| Recall archeologique | 0.660 |
| F1 archeologique | 0.707 |
| Faux negatifs | 36 |
| Faux positifs | 22 |

Par rapport au reglage de base equivalent :

| Reglage | Accuracy | F1 archeologique | Faux negatifs | Faux positifs |
|---|---:|---:|---:|---:|
| Baseline ancienne | 0.760 | 0.667 | 36 | 34 |
| Modele optimise | 0.801 | 0.707 | 36 | 22 |

L'optimisation reduit surtout les faux positifs, sans augmenter les faux negatifs.

## Analyse des erreurs

Rapports d'erreurs optimises :

- `data/combined/fusion_error_report_tuned.csv`
- `data/combined/fusion_error_report_tuned.md`

Resume :

| Type | Nombre |
|---|---:|
| Images testees | 292 |
| Predictions correctes | 234 |
| Faux negatifs | 36 |
| Faux positifs | 22 |

Sites concentrant le plus d'erreurs :

| Site | Faux negatifs | Faux positifs | Total |
|---|---:|---:|---:|
| `site02` | 1 | 10 | 11 |
| `site12` | 4 | 4 | 8 |
| `site01` | 1 | 4 | 5 |
| `site06` | 5 | 0 | 5 |
| `site08` | 5 | 0 | 5 |
| `site09` | 5 | 0 | 5 |
| `site15` | 5 | 0 | 5 |

Interpretation :

- `site02` produit surtout des faux positifs : certains patches negatifs ressemblent fortement a des formes archeologiques.
- `site09`, `site15`, `site08` et `site06` produisent surtout des faux negatifs : le modele rate plusieurs patches archeologiques.
- Les faux positifs viennent des patches `neg`.
- Les faux negatifs viennent des patches `patch` et `large`.

## Visualisations

Les figures sont disponibles dans :

- `data/combined/figures/`

Fichiers principaux :

- `data/combined/figures/confusion_matrix.svg`
- `data/combined/figures/probability_histogram.svg`
- `data/combined/figures/errors_by_site.svg`
- `data/combined/figures/errors_by_patch_type.svg`
- `data/combined/figures/visualization_summary.md`

Ces figures permettent de visualiser :

- la matrice de confusion ;
- la distribution des probabilites `P(archeologique)` ;
- les erreurs par site ;
- les erreurs par type de patch.

## Limites actuelles

Le modele actuel reste une baseline de classification par patch.

Limites principales :

- il ne localise pas automatiquement les sites dans une grande image ;
- il ne donne pas de contour precis ;
- il depend fortement de la qualite des patches exportes ;
- il peut confondre certaines formes modernes ou paysageres avec des vestiges ;
- ResNet-18 n'est pas encore fine-tune sur les images archeologiques ;
- le dataset reste petit pour du deep learning.

## Conclusions actuelles

La fusion RGB + LiDAR est confirmee comme la meilleure approche actuelle.

Le meilleur modele actuel est :

```text
ResNet-18 preentraine RGB + ResNet-18 preentraine LiDAR
+ concatenation des embeddings
+ regression logistique optimisee
```

Avec :

```text
scaler = none
class_weight = none
C = 0.03
threshold = 0.45
```

Performance actuelle :

```text
Accuracy = 0.801
F1 archeologique = 0.707
```

Cette baseline est suffisamment solide pour servir de reference avant toute tentative de fine-tuning ou de detection.

## Prochaines pistes recommandees

Sans modifier le dataset :

1. Documenter le modele actuel dans le rapport de stage.
2. Utiliser les figures comme support d'analyse.
3. Comparer deux modes de decision :
   - mode strict, moins de faux positifs ;
   - mode prospection, moins de faux negatifs.
4. Preparer un script de prediction pour de nouveaux patches RGB + LiDAR.

Avec modification du dataset :

1. Corriger `site15_neg01` et `site15_neg02`.
2. Ajouter un patch archeologique pour `site13`.
3. Inspecter les faux positifs forts de `site02`.
4. Inspecter les faux negatifs forts de `site09`, `site15`, `site08` et `site06`.
5. Ajouter des negatifs difficiles si l'objectif est de reduire les faux positifs.

Avec evolution du modele :

1. Tester un fine-tuning prudent de ResNet-18.
2. Comparer le fine-tuning a cette baseline.
3. Preparer ensuite un modele de detection type YOLO si l'objectif devient de scanner de grandes images.
