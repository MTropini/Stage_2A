from datetime import datetime

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
    QgsWkbTypes,
)


# Run this script inside QGIS: Plugins > Python Console > Show Editor > Run.

SITE_LAYER_NAME = "site-romain-france"
OUTPUT_DIR = r"C:\Users\Mathieu\Documents\New project\Stage_2A\data\exports_qgis"
OUTPUT_BASENAME = "patches_auto_sites_romains"
OUTPUT_LAYER_NAME = "patches_auto_sites_romains"

SITE_ID_FIELD = "id"
SITE_NAME_FIELD = "Nom"
SITE_TYPE_FIELD = "Type"

# Patch generation rules:
# - patch follows the original site polygon geometry.
# - large and tres_large use the site's extent plus a margin, in project CRS map units.
# If your project is in a metric CRS, margin values are meters.
PATCH_SPECS = [
    ("patch", None),
    ("large", 100.0),
    ("tres_large", 250.0),
]


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
    output_layer = _create_memory_layer(output_crs.authid())

    provider = output_layer.dataProvider()
    features = []

    for index, site_feature in enumerate(site_layer.getFeatures(), start=1):
        geometry = QgsGeometry(site_feature.geometry())
        if geometry.isEmpty():
            continue

        if site_layer.crs() != output_crs:
            geometry.transform(transform)

        site_id = _site_id(site_feature, index)
        site_name = _field_value(site_feature, SITE_NAME_FIELD)
        site_type = _field_value(site_feature, SITE_TYPE_FIELD)
        for patch_type, margin in PATCH_SPECS:
            patch_feature = QgsFeature(output_layer.fields())
            patch_feature.setGeometry(_patch_geometry(geometry, patch_type, margin))
            patch_feature["patch_id"] = f"{site_id}_{patch_type}"
            patch_feature["site_id"] = site_id
            patch_feature["site_name"] = site_name
            patch_feature["site_type"] = site_type
            patch_feature["classe"] = "archeologique"
            patch_feature["patch_type"] = patch_type
            patch_feature["margin_m"] = margin if margin is not None else 0.0
            patch_feature["source"] = "site-romain-france"
            patch_feature["commentaire"] = "patch positif genere automatiquement"
            features.append(patch_feature)

    provider.addFeatures(features)
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

    print(f"Sites lus: {site_layer.featureCount()}")
    print(f"Patchs generes: {len(features)}")
    print(f"Fichier cree: {output_gpkg}")
    print(f"Couche: {OUTPUT_LAYER_NAME}")


def _get_layer(name):
    layers = QgsProject.instance().mapLayersByName(name)
    if not layers:
        raise ValueError(f"Couche introuvable dans QGIS: {name}")
    return layers[0]


def _output_path():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return rf"{OUTPUT_DIR}\{OUTPUT_BASENAME}_{timestamp}.gpkg"


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
    fields.append(QgsField("margin_m", QVariant.Double))
    fields.append(QgsField("source", QVariant.String, len=120))
    fields.append(QgsField("commentaire", QVariant.String, len=255))

    provider.addAttributes(fields)
    layer.updateFields()
    return layer


def _site_id(feature, fallback_index):
    value = _field_value(feature, SITE_ID_FIELD)
    if value:
        try:
            return f"site{int(float(value)):02d}"
        except ValueError:
            return _clean_identifier(value)
    return f"site{fallback_index:02d}"


def _field_value(feature, field_name):
    if field_name not in feature.fields().names():
        return ""
    value = feature[field_name]
    if value is None:
        return ""
    return str(value).strip()


def _clean_identifier(value):
    clean = []
    for char in value.lower():
        if char.isalnum():
            clean.append(char)
        elif char in {" ", "_", "-"}:
            clean.append("_")
    return "".join(clean).strip("_") or "site"


def _extent_with_margin(extent, margin):
    rectangle = QgsRectangle(
        extent.xMinimum() - margin,
        extent.yMinimum() - margin,
        extent.xMaximum() + margin,
        extent.yMaximum() + margin,
    )
    return QgsGeometry.fromRect(rectangle)


def _patch_geometry(site_geometry, patch_type, margin):
    if patch_type == "patch":
        return QgsGeometry(site_geometry)
    return _extent_with_margin(site_geometry.boundingBox(), margin)


main()
