from datetime import datetime
from math import cos, pi, sin
from random import Random

from qgis.PyQt.QtCore import QVariant
from qgis.core import (
    QgsCoordinateTransform,
    QgsFeature,
    QgsField,
    QgsFields,
    QgsGeometry,
    QgsProject,
    QgsRectangle,
    QgsVectorFileWriter,
    QgsVectorLayer,
)


# Run this script inside QGIS: Plugins > Python Console > Show Editor > Run.

SITE_LAYER_NAME = "site-romain-france"
OUTPUT_DIR = r"C:\Users\Mathieu\Documents\New project\Stage_2A\data\exports_qgis_auto"
OUTPUT_BASENAME = "negative_patch_polygons"
OUTPUT_LAYER_NAME = "negative_patch_polygons"

SITE_ID_FIELD = "id"
SITE_NAME_FIELD = "Nom"
SITE_TYPE_FIELD = "Type"

# Set the site id range to process.
MIN_SITE_ID = 1
MAX_SITE_ID = 15

NEGATIVES_PER_SITE = 6
RANDOM_SEED = 42

# Candidate centers are sampled in a ring around the site centroid.
# Values are in project CRS map units, normally meters.
MIN_DISTANCE_FROM_SITE = 150.0
MAX_DISTANCE_FROM_SITE = 900.0

# Negative patch size is based on the site's bounding box, but bounded.
MIN_PATCH_SIDE = 120.0
MAX_PATCH_SIDE = 350.0

# Avoid known sites with this extra safety margin.
SITE_BUFFER_MARGIN = 30.0

MAX_ATTEMPTS_PER_SITE = 1000


def main():
    project = QgsProject.instance()
    site_layer = _get_layer(SITE_LAYER_NAME)
    output_crs = project.crs()

    if output_crs.isGeographic():
        raise ValueError(
            "Le SCR du projet est en degres. Mets le projet dans un SCR en metres "
            "(par exemple EPSG:2154) avant de lancer ce script."
        )

    transform = QgsCoordinateTransform(site_layer.crs(), output_crs, project)
    source_sites = []
    all_site_geometries = []

    for index, feature in enumerate(site_layer.getFeatures(), start=1):
        geometry = QgsGeometry(feature.geometry())
        if geometry.isEmpty():
            continue

        if site_layer.crs() != output_crs:
            geometry.transform(transform)

        site_id_number = _site_id_number(feature, index)
        all_site_geometries.append(geometry)

        if MIN_SITE_ID <= site_id_number <= MAX_SITE_ID:
            source_sites.append((feature, geometry, site_id_number))

    if not source_sites:
        raise ValueError(f"Aucun site trouve entre site{MIN_SITE_ID:02d} et site{MAX_SITE_ID:02d}.")

    forbidden_geometry = QgsGeometry.unaryUnion(all_site_geometries).buffer(SITE_BUFFER_MARGIN, 12)
    output_layer = _create_memory_layer(output_crs.authid())
    provider = output_layer.dataProvider()
    rng = Random(RANDOM_SEED)

    output_features = []
    for feature, site_geometry, site_id_number in source_sites:
        site_id = f"site{site_id_number:02d}"
        site_name = _field_value(feature, SITE_NAME_FIELD)
        site_type = _field_value(feature, SITE_TYPE_FIELD)
        site_center = site_geometry.centroid().asPoint()
        width, height = _negative_patch_size(site_geometry.boundingBox())

        generated = 0
        attempts = 0
        while generated < NEGATIVES_PER_SITE and attempts < MAX_ATTEMPTS_PER_SITE:
            attempts += 1
            candidate = _random_candidate_rectangle(site_center, width, height, rng)
            candidate_geometry = QgsGeometry.fromRect(candidate)

            if candidate_geometry.intersects(forbidden_geometry):
                continue

            generated += 1
            patch_feature = QgsFeature(output_layer.fields())
            patch_feature.setGeometry(candidate_geometry)
            patch_feature["patch_id"] = f"{site_id}_neg_auto{generated:02d}"
            patch_feature["site_id"] = site_id
            patch_feature["site_name"] = site_name
            patch_feature["site_type"] = site_type
            patch_feature["classe"] = "non_archeologique"
            patch_feature["patch_type"] = "neg_auto"
            patch_feature["width_m"] = width
            patch_feature["height_m"] = height
            patch_feature["source"] = "generated_negative_candidates"
            patch_feature["commentaire"] = "patch negatif automatique a verifier dans QGIS"
            output_features.append(patch_feature)

        print(f"{site_id}: {generated}/{NEGATIVES_PER_SITE} negatifs generes")

    provider.addFeatures(output_features)
    output_layer.updateExtents()

    output_gpkg = _output_path()
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GPKG"
    options.layerName = OUTPUT_LAYER_NAME
    options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile

    error, message, _, _ = QgsVectorFileWriter.writeAsVectorFormatV3(
        output_layer,
        output_gpkg,
        project.transformContext(),
        options,
    )

    if error != QgsVectorFileWriter.NoError:
        raise RuntimeError(f"Erreur export GeoPackage: {message}")

    saved_layer = QgsVectorLayer(f"{output_gpkg}|layername={OUTPUT_LAYER_NAME}", OUTPUT_LAYER_NAME, "ogr")
    if saved_layer.isValid():
        project.addMapLayer(saved_layer)

    print(f"Sites sources: {len(source_sites)}")
    print(f"Patchs negatifs generes: {len(output_features)}")
    print(f"Fichier cree: {output_gpkg}")
    print(f"Couche: {OUTPUT_LAYER_NAME}")


def _get_layer(name):
    layers = QgsProject.instance().mapLayersByName(name)
    if not layers:
        raise ValueError(f"Couche introuvable dans QGIS: {name}")
    return layers[0]


def _create_memory_layer(crs_authid):
    layer = QgsVectorLayer(f"Polygon?crs={crs_authid}", OUTPUT_LAYER_NAME, "memory")
    provider = layer.dataProvider()

    fields = QgsFields()
    fields.append(QgsField("patch_id", QVariant.String, len=80))
    fields.append(QgsField("site_id", QVariant.String, len=40))
    fields.append(QgsField("site_name", QVariant.String, len=120))
    fields.append(QgsField("site_type", QVariant.String, len=80))
    fields.append(QgsField("classe", QVariant.String, len=40))
    fields.append(QgsField("patch_type", QVariant.String, len=40))
    fields.append(QgsField("width_m", QVariant.Double))
    fields.append(QgsField("height_m", QVariant.Double))
    fields.append(QgsField("source", QVariant.String, len=120))
    fields.append(QgsField("commentaire", QVariant.String, len=255))

    provider.addAttributes(fields)
    layer.updateFields()
    return layer


def _site_id_number(feature, fallback_index):
    value = _field_value(feature, SITE_ID_FIELD)
    if value:
        try:
            return int(float(value))
        except ValueError:
            return fallback_index
    return fallback_index


def _field_value(feature, field_name):
    if field_name not in feature.fields().names():
        return ""
    value = feature[field_name]
    if value is None:
        return ""
    return str(value).strip()


def _negative_patch_size(extent):
    width = _bounded(extent.width(), MIN_PATCH_SIDE, MAX_PATCH_SIDE)
    height = _bounded(extent.height(), MIN_PATCH_SIDE, MAX_PATCH_SIDE)
    return width, height


def _bounded(value, minimum, maximum):
    return max(minimum, min(maximum, float(value)))


def _random_candidate_rectangle(site_center, width, height, rng):
    angle = rng.uniform(0.0, 2.0 * pi)
    distance = rng.uniform(MIN_DISTANCE_FROM_SITE, MAX_DISTANCE_FROM_SITE)
    center_x = site_center.x() + cos(angle) * distance
    center_y = site_center.y() + sin(angle) * distance

    return QgsRectangle(
        center_x - width / 2.0,
        center_y - height / 2.0,
        center_x + width / 2.0,
        center_y + height / 2.0,
    )


def _output_path():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return rf"{OUTPUT_DIR}\{OUTPUT_BASENAME}_{timestamp}.gpkg"


main()
