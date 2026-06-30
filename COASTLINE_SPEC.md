# Segmentation du trait de cote

Objectif : detecter automatiquement la limite eau/terre a partir d'images
cotieres, puis comparer des methodes classiques et des modeles de segmentation.

## Donnees necessaires

Donnees minimales :

- orthophotos ou images satellite cotieres ;
- si possible GeoTIFF pour conserver les coordonnees ;
- resolution et date d'acquisition connues.

Donnees ideales :

- orthophoto RGB ou RGB+NIR ;
- masques eau/terre annotes pour apprentissage supervise ;
- traits de cote de reference sous forme vectorielle ;
- images multi-dates pour suivi temporel.

## Taches possibles

1. Segmentation eau/terre :

```text
image -> masque eau/terre
```

2. Extraction du trait de cote :

```text
masque eau/terre -> frontiere eau/terre
```

3. Comparaison temporelle :

```text
trait de cote date 1 vs trait de cote date 2
```

## Baseline actuelle

Le script `scripts/segment_coastline.py` applique une methode classique :

- calcul d'un indice d'eau simple a partir de RGB ;
- seuil automatique d'Otsu ;
- masque eau/terre ;
- extraction de la frontiere du masque ;
- export d'une superposition du trait de cote sur l'image.

Cette methode ne remplace pas un modele IA. Elle sert de baseline rapide et
interpretable.

## Baseline supervisee ajoutee

Le pipeline supervise suit la meme logique que la classification archeologique :

```text
donnees annotees -> entrainement Random Forest -> prediction -> masque + overlay
```

Structure attendue :

```text
data/coastline/training/
  images/
  masks/
```

Les images et les masques doivent avoir le meme nom de base. Exemple :

```text
images/olbia_01.png
masks/olbia_01.png
```

Convention des masques :

```text
0 / noir = terre
255 / blanc = eau
```

Scripts :

- `scripts/train_coastline_rf.py` entraine un Random Forest pixel par pixel ;
- `scripts/predict_coastline_rf.py` applique le modele sur les images cotieres ;
- `src/stage2a/coastline_dataset.py` charge et echantillonne les pixels annotes ;
- `src/stage2a/coastline.py` contient les fonctions de score, masque, frontiere
  et export.

Le modele est sauvegarde dans :

```text
models/random_forest_coastline.pkl
```

Les sorties de prediction sont ecrites dans :

```text
data/coastline/processed_rf/
```

Cette baseline reste simple mais elle permet deja de comparer :

- segmentation RGB non supervisee par indice d'eau ;
- segmentation supervisee par Random Forest ;
- plus tard, segmentation profonde type U-Net ou SegFormer.

## Evaluation recommandee

Pour chaque image annotee, conserver une separation claire entre zones
d'entrainement et zones de test afin d'eviter une evaluation trop optimiste.

Metriques a ajouter ensuite :

- precision, recall et F1 par classe eau/terre ;
- IoU eau ;
- distance moyenne entre trait de cote predit et trait de cote reference ;
- analyse visuelle des erreurs dans QGIS.

## Comparaison interannuelle

Le script `scripts/compare_coastline_years.py` compare les masques de trait de
cote detectes pour plusieurs annees. Les noms de fichiers doivent contenir
l'annee, par exemple :

```text
2013_coastline_mask.png
2015_coastline_mask.png
2019_coastline_mask.png
2025_coastline_mask.png
2026_coastline_mask.png
```

Pour chaque paire consecutive, il calcule :

- distance moyenne d'un trait vers l'autre ;
- mediane ;
- percentile 95 ;
- distance maximale ;
- moyenne symetrique.

Si un fichier world accompagne le masque, les distances sont en unites de carte
du projet QGIS. Sinon, elles sont en pixels. Les resultats sont sauvegardes dans :

```text
data/coastline/change/coastline_change_summary.csv
```

Cette premiere mesure donne l'amplitude du changement. Pour transformer cette
amplitude en recul/avancee du trait de cote, l'etape suivante sera une analyse
par transects perpendiculaires a la cote.

## Donnees orthophoto multi-dates

Pour les orthophotos fournies par annee, utiliser :

```text
data/coastline/orthophoto/<annee>/
data/coastline/metadata/coastline_sources.csv
data/coastline/metadata/coastline_pairs.csv
```

`coastline_sources.csv` decrit chaque orthophoto source. `coastline_pairs.csv`
regroupe les images d'un meme secteur a travers les annees.

Le fichier `COASTLINE_MULTIMODAL_DATA.md` contient le protocole complet. Le LiDAR
reste optionnel pour une evolution future.

## Prochaines methodes a comparer

- indices spectraux si NIR disponible : NDWI, MNDWI ;
- Random Forest pixel par pixel ;
- U-Net pour segmentation supervisee ;
- DeepLabV3+ ou SegFormer si la base annotee devient suffisante.
