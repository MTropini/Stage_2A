# Specification de la base de donnees

Objectif : construire une base de donnees reproductible pour predire si une
zone candidate contient un site archeologique ou non, puis comparer l'apport
des orthophotos seules et de la fusion orthophoto + LiDAR.

## Unite d'observation

L'unite de base est un patch geospatial centre sur une zone candidate.

Chaque patch doit avoir :

- une image orthophoto RGB ;
- si disponible, un ou plusieurs derives LiDAR alignes ;
- un label binaire ;
- des metadonnees de localisation et de source.

Labels :

```text
0 = non_archeologique
1 = archeologique
```

## Sources de donnees a privilegier

### Orthophotos

Sources prioritaires :

- BD ORTHO IGN ;
- orthophotos departementales ou regionales disponibles en GeoTIFF ;
- export QGIS depuis un flux WMTS/WMS uniquement pour prototypage.

Critere important : privilegier les GeoTIFF locaux quand c'est possible, car
ils conservent la resolution, la projection et l'emprise.

### LiDAR

Sources prioritaires :

- RGE ALTI / donnees LiDAR HD si disponibles ;
- MNT derive du LiDAR ;
- produits derives calcules dans QGIS ou Python.

Derives LiDAR candidats :

- MNT normalise ;
- hillshade ;
- slope ;
- local relief model ;
- sky view factor ;
- openness positive/negative si disponible.

## Variables a conserver

### Variables image

Pour chaque patch orthophoto :

- canaux RGB ;
- statistiques RGB ;
- intensite en niveaux de gris ;
- contraste local ;
- texture simple ;
- resolution spatiale.

Pour chaque patch LiDAR :

- valeurs du derive LiDAR ;
- statistiques min, max, moyenne, ecart-type ;
- gradients locaux ;
- texture / rugosite ;
- resolution spatiale.

### Metadonnees

Chaque patch doit pouvoir etre relie a :

- identifiant unique ;
- classe ;
- source orthophoto ;
- source LiDAR ;
- date ou millesime de l'image ;
- projection ;
- resolution ;
- coordonnees de l'emprise ;
- methode de selection ;
- commentaire expert si utile.

## Organisation recommandee

Structure simple pour les premiers modeles :

```text
data/
  classification/
    archeologique/
    non_archeologique/
  classification_lidar/
    archeologique/
    non_archeologique/
  metadata/
    patches.csv
```

Nommage recommande :

```text
olbia_arch_001.png
olbia_arch_lidar_001.png
olbia_non_arch_001.png
olbia_non_arch_lidar_001.png
```

Le fichier `patches.csv` devra contenir au minimum :

```text
patch_id,classe,site,source_rgb,source_lidar,xmin,ymin,xmax,ymax,crs,resolution,date,commentaire
```

## Strategie d'echantillonnage

La base doit contenir plusieurs types d'exemples.

### Exemples positifs

Inclure :

- sites bien visibles ;
- sites partiellement visibles ;
- murs ou plans de batiments ;
- fosses ou traces lineaires ;
- microreliefs visibles surtout au LiDAR ;
- differents sols, vegetations et contextes.

### Exemples negatifs

Inclure des zones difficiles :

- routes ;
- parkings ;
- batiments modernes ;
- chemins ;
- champs ;
- murs modernes ;
- zones seches ;
- vegetation ;
- zones proches des sites mais sans vestiges.

Les exemples negatifs doivent etre proches visuellement des positifs pour eviter
un apprentissage trop facile et non generalisable.

## Tailles de patchs a tester

Tester plusieurs tailles, car le bon contexte spatial n'est pas connu au depart :

```text
64 x 64 pixels
128 x 128 pixels
256 x 256 pixels
512 x 512 pixels
```

Pour le prototype actuel, garder des exports de taille comparable. Pour le
pipeline final, extraire automatiquement des patchs a taille fixe depuis les
rasters sources.

## Comparaisons experimentales prevues

Comparer progressivement :

1. orthophoto RGB seule ;
2. LiDAR seul ;
3. RGB + hillshade ;
4. RGB + slope ;
5. RGB + plusieurs derives LiDAR ;
6. modeles classiques vs deep learning.

Modeles baseline :

- Random Forest ;
- SVM ;
- XGBoost ou LightGBM si pertinent.

Modeles avances :

- CNN de classification ;
- U-Net ou SegFormer si passage a la segmentation ;
- detection d'objets si annotations par boites.

## Regles de validation

Eviter de melanger dans train et test des patchs presque identiques ou voisins.

Validation minimale :

- cross-validation stratifiee pour les premiers essais ;
- split par site ou par zone quand la base grossit ;
- matrice de confusion ;
- precision, recall, F1-score ;
- analyse des erreurs.

Le split par zone sera plus realiste que le split aleatoire, car il teste la
capacite du modele a generaliser a un nouveau secteur.

## Prochaine etape concrete

Avant d'ajouter beaucoup d'images, construire un premier `patches.csv` et choisir :

- les sources orthophoto ;
- les derives LiDAR retenus ;
- la taille standard des patchs ;
- les zones positives et negatives ;
- la strategie de validation.

Ensuite seulement, automatiser l'extraction depuis QGIS ou Python.
