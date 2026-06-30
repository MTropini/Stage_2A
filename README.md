# Stage_2A

Projet de stage R&D sur l'utilisation de l'IA pour la teledetection :

- detection, classification et segmentation de sites archeologiques ;
- extraction et segmentation du trait de cote ;
- experimentation sur orthophotos, images TIFF/GeoTIFF et donnees derivees LiDAR.

## Structure

```text
data/
  raw/          Images originales a analyser
  processed/    Figures et resultats generes
scripts/
  inspect_images.py
src/
  stage2a/
    image_io.py
    preprocessing.py
    visualization.py
```

## Premier test d'import d'images

Si Python est installe sur ta machine, installe les dependances minimales :

```bash
python -m pip install -r requirements.txt
```

Place quelques fichiers image dans :

```text
data/raw/
```

Formats acceptes pour ce premier essai :

- `.jpg`
- `.png`
- `.tif`
- `.tiff`
- `.bmp`
- `.webp`

Puis lance :

```bash
python scripts/inspect_images.py
```

Le script affiche les informations principales de chaque image et cree une figure
dans `data/processed/` avec :

- image originale ;
- conversion en niveaux de gris ;
- contraste normalise ;
- masque obtenu par seuillage simple.

Ce premier script ne remplace pas un vrai pipeline geospatial. Il sert a comprendre
les bases de l'import et du pretraitement. Pour les GeoTIFF georeferences, on ajoutera
ensuite `rasterio` afin de conserver les metadonnees spatiales.

## Premiere classification archeologique / non archeologique

Pour entrainer un premier modele classique, place des petites images ou patchs dans :

```text
data/classification/
  archeologique/
    site_01.png
    site_02.png
  non_archeologique/
    fond_01.png
    fond_02.png
```

Chaque image doit correspondre a une zone candidate :

- `archeologique` : la zone contient un site ou une structure archeologique visible ;
- `non_archeologique` : la zone ne contient pas de site archeologique.

Puis lance :

```bash
python scripts/train_archaeology_rf.py
```

Le modele Random Forest est sauvegarde dans :

```text
models/random_forest_archaeology.pkl
```

Pour predire une nouvelle image :

```bash
python scripts/predict_archaeology_rf.py data/raw/orthophoto_olbia.png
```

Ce premier modele est un baseline : il utilise des caracteristiques simples
derivees des couleurs, du contraste et de la texture. Il sert a etablir une
premiere reference avant de passer a des methodes plus avancees.

## Fusion orthophoto + LiDAR

Pour tester si le LiDAR ameliore le modele, ajoute des images derivees LiDAR
dans une structure parallele :

```text
data/classification_lidar/
  archeologique/
    olbia_arch_1.png
    olbia_arch_2.png
  non_archeologique/
    olbia_non_arch_1.png
    olbia_non_arch_2.png
```

Les noms de base doivent correspondre aux patchs orthophoto :

```text
data/classification/archeologique/olbia_arch_1.png
data/classification_lidar/archeologique/olbia_arch_1.png
```

Les images LiDAR peuvent etre des produits derives : hillshade, pente, MNT
normalise, Local Relief Model ou Sky View Factor.

Puis lance :

```bash
python scripts/train_archaeology_rf_multimodal.py
```

Ce script concatene les caracteristiques de l'orthophoto et du LiDAR, puis
entraine une Random Forest. On compare ensuite ce score avec le modele image
seule pour evaluer l'apport du LiDAR.

## Segmentation du trait de cote

Place des images cotieres dans :

```text
data/coastline/raw/
```

Puis lance :

```bash
python scripts/segment_coastline.py
```

Le script cree dans `data/coastline/processed/` :

- un score d'eau ;
- un masque eau/terre ;
- un masque du trait de cote ;
- une image avec le trait de cote superpose en rouge.

Cette premiere methode est une baseline classique RGB. Pour un pipeline
scientifique plus robuste, on ajoutera ensuite des donnees georeferencees,
des masques eau/terre de reference et des modeles de segmentation comme U-Net.

## Segmentation supervisee du trait de cote

Pour avancer en parallele de la classification archeologique, on peut aussi
entrainer un premier modele supervise eau/terre a partir de masques annotes :

```text
data/coastline/training/
  images/
    olbia_01.png
  masks/
    olbia_01.png
```

Les noms de base doivent correspondre entre image et masque. Dans les masques :

- noir = terre ;
- blanc = eau.

Puis lance :

```bash
python scripts/train_coastline_rf.py
```

Le modele Random Forest pixel par pixel est sauvegarde dans :

```text
models/random_forest_coastline.pkl
```

Pour predire le masque eau/terre et extraire le trait de cote sur les images de
`data/coastline/raw/` :

```bash
python scripts/predict_coastline_rf.py
```

Le script cree dans `data/coastline/processed_rf/` :

- un score d'eau predit ;
- un masque eau/terre ;
- un masque du trait de cote ;
- une superposition du trait de cote sur l'image.

## Comparaison temporelle du trait de cote

Pour comparer plusieurs annees, nomme les orthophotos avec leur annee :

```text
data/coastline/raw/
  2013.png
  2015.png
  2019.png
  2025.png
  2026.png
```

Detecte d'abord le trait de cote :

```bash
python scripts/segment_coastline.py
```

Puis compare les masques de trait de cote detectes :

```bash
python scripts/compare_coastline_years.py --mask-dir data/coastline/processed_orthophoto --max-points 2000
```

Le script genere :

```text
data/coastline/change/coastline_change_summary.csv
```

Les distances sont exprimees en unites cartographiques si les images ont un
fichier world associe (`.pgw`, `.wld`, `.pngw`, etc.). Sinon elles sont exprimees
en pixels. Cette comparaison mesure l'ecart spatial entre les traits ; pour
distinguer explicitement recul et avancee du littoral, on ajoutera ensuite des
transects perpendiculaires a la cote.

## Donnees orthophoto pour le littoral

Les orthophotos multi-dates sont organisees dans la structure suivante :

```text
data/coastline/
  orthophoto/
    2013/
    2015/
    2019/
    2025/
    2026/
  metadata/
    coastline_sources.csv
    coastline_pairs.csv
```

Le document `COASTLINE_MULTIMODAL_DATA.md` decrit l'organisation actuelle en
orthophoto seule. Le LiDAR pourra etre ajoute plus tard si les donnees deviennent
disponibles.

## Verification des exports QGIS

Pour verifier les exports RGB/LiDAR avant entrainement :

```bash
python scripts/audit_exported_dataset.py
```

Le script verifie :

- nombre de patchs par classe ;
- nombre de sites detectes ;
- paires RGB/LiDAR manquantes ;
- tailles RGB/LiDAR incoherentes ;
- fichiers world `.pgw` manquants ;
- noms de fichiers suspects.

Il genere aussi :

```text
data/exports_qgis/dataset_audit.csv
```

## Modele ResNet-18 RGB

Pour evaluer un CNN preentraine sur les exports QGIS :

```bash
python scripts/train_resnet18_rgb.py
```

Par defaut, le script :

- lit `data/exports_qgis/dataset_audit.csv` ;
- exclut les vues `tres_large` ;
- utilise ResNet-18 preentraine sur ImageNet ;
- entraine seulement la derniere couche de classification ;
- evalue avec un split leave-one-site-out.

Pour entrainer aussi le backbone complet :

```bash
python scripts/train_resnet18_rgb.py --fine-tune
```

Sur CPU, la version la plus rapide consiste a utiliser ResNet-18 comme
extracteur de representations preentrainees :

```bash
python scripts/evaluate_resnet18_embeddings.py
```

Pour evaluer les images LiDAR seules avec la meme logique :

```bash
python scripts/evaluate_resnet18_lidar_embeddings.py
```

Pour comparer directement RGB seul, LiDAR seul et fusion RGB+LiDAR sur les
memes splits :

```bash
python scripts/compare_resnet18_modalities.py
```

## Generation automatique de patchs positifs

Si tu as une couche QGIS contenant les sites connus, tu peux generer
automatiquement les polygones `patch`, `large` et `tres_large` :

```bash
python scripts/generate_positive_patch_polygons.py --sites data/exports_qgis/sites_romains.gpkg --site-id-field site_id --target-crs EPSG:2154
```

Le script cree par defaut :

```text
data/exports_qgis/positive_patch_polygons.gpkg
```

Tu peux ensuite charger cette couche dans QGIS et l'utiliser comme couche de
couverture de l'Atlas pour exporter les images RGB puis LiDAR.

Pour connaitre le nom des couches et des champs d'un GeoPackage :

```bash
python scripts/list_vector_layers.py data/exports_qgis/sites_romains.gpkg
```

Pour generer des candidats negatifs autour des sites directement dans QGIS,
execute le script PyQGIS :

```text
qgis_scripts/generate_negative_patch_polygons_qgis.py
```

Les candidats generes doivent etre verifies visuellement dans QGIS avant export.

## Combiner plusieurs exports

Pour prendre en compte les exports manuels et les exports automatiques :

```bash
python scripts/combine_dataset_audits.py
```

Le manifeste combine est ecrit ici :

```text
data/combined/dataset_audit.csv
```

Il peut ensuite etre donne aux scripts d'evaluation avec `--audit-csv`.
