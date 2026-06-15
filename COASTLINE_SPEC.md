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

## Prochaines methodes a comparer

- indices spectraux si NIR disponible : NDWI, MNDWI ;
- Random Forest pixel par pixel ;
- U-Net pour segmentation supervisee ;
- DeepLabV3+ ou SegFormer si la base annotee devient suffisante.

