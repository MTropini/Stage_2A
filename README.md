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
