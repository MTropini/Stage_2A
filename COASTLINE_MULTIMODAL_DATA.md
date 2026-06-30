# Donnees orthophoto pour le trait de cote

Objectif : organiser les orthophotos par annee et par secteur afin de detecter
le trait de cote, puis de comparer son evolution dans le temps.

Le LiDAR n'est pas utilise dans cette version du protocole. Il pourra etre
ajoute plus tard comme modalite complementaire si des donnees deviennent
disponibles.

## Donnees disponibles

Les orthophotos sont organisees ainsi :

```text
data/coastline/orthophoto/
  2013/
    output_1.png
    output_1.pgw
    ...
    output_6.png
    output_6.pgw
  2015/
  2019/
  2025/
  2026/
```

Chaque annee contient 6 secteurs :

```text
output_1
output_2
output_3
output_4
output_5
output_6
```

Les fichiers `.pgw` doivent rester a cote des PNG. Ils permettent d'obtenir des
distances cartographiques au lieu de simples distances en pixels.

## Manifestes

Deux fichiers de metadonnees decrivent la base :

```text
data/coastline/metadata/coastline_sources.csv
data/coastline/metadata/coastline_pairs.csv
```

`coastline_sources.csv` contient une ligne par image source.

`coastline_pairs.csv` regroupe les images d'un meme secteur a travers les
annees. C'est ce fichier qui permet de comparer, par exemple, `output_3` entre
2013, 2015, 2019, 2025 et 2026.

## Controle effectue

Les orthophotos actuellement deposees ont toutes :

- largeur : 3507 px ;
- hauteur : 2480 px ;
- un fichier `.pgw` associe ;
- une resolution proche de 0,15 m par pixel.

Cette homogeneite est bonne pour la comparaison temporelle.

## Workflow de detection

Lancer la detection automatique sur toutes les orthophotos :

```bash
python scripts/segment_coastline_orthophotos.py
```

Le script lit :

```text
data/coastline/orthophoto/<annee>/
```

et ecrit :

```text
data/coastline/processed_orthophoto/<annee>/
```

Pour chaque image, il genere :

- score d'eau ;
- masque eau/terre ;
- masque du trait de cote ;
- image overlay avec le trait de cote en rouge.

## Workflow de comparaison

Comparer les traits detectes entre annees :

```bash
python scripts/compare_coastline_years.py --mask-dir data/coastline/processed_orthophoto --max-points 2000
```

Le script compare chaque secteur separement :

```text
output_1 : 2013 -> 2015 -> 2019 -> 2025 -> 2026
output_2 : 2013 -> 2015 -> 2019 -> 2025 -> 2026
...
output_6 : 2013 -> 2015 -> 2019 -> 2025 -> 2026
```

Le tableau de resultats est ecrit ici :

```text
data/coastline/change/coastline_change_summary.csv
```

## Limite importante

La detection actuelle est une baseline RGB automatique. Elle peut confondre :

- eau sombre et ombre ;
- plage claire et bati clair ;
- zones humides et eau ;
- enrochements, digues et routes littorales.

Les overlays doivent donc etre verifies visuellement dans QGIS. Si la baseline
est insuffisante, la prochaine etape sera de creer quelques masques manuels
eau/terre pour entrainer le modele supervise `train_coastline_rf.py`.
