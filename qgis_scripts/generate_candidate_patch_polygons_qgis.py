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


# Select the layer containing the candidate targets in QGIS before running.
# Run from: Plugins > Python Console > Show Editor > Run.

OUTPUT_DIR = r"C:\Users\Mathieu\Documents\New project\Stage_2A\data\candidates_qgis"
OUTPUT_BASENAME = "patches_auto_candidats"
OUTPUT_LAYER_NAME = "patches_auto_candidats"

# Optional fields. If absent, candidate01, candidate02... are generated.
CANDIDATE_ID_FIELD = "id"
CANDIDATE_NAME_FIELD = "Nom"

PATCH_SPECS = [
    ("patch", None),
    ("large", 100.0),
    ("tres_large", 250.0),
]


def main():
    project = QgsProject.instance()
    target_layer = _active_vector_layer()
    output_crs = project.crs()

    if output_crs.isGeographic():
        raise ValueError(
            "Le SCR du projet est en degres. Mets le projet en EPSG:2154 "
            "ou dans un autre SCR metrique avant de lancer le script."
        )

    transform = QgsCoordinateTransform(target_layer.crs(), output_crs, project)
    output_layer = _create_memory_layer(output_crs.authid())
    features = []

    for index, target_feature in enumerate(target_layer.getFeatures(), start=1):
        geometry = QgsGeometry(target_feature.geometry())
        if geometry.isEmpty():
            continue

        if target_layer.crs() != output_crs:
            geometry.transform(transform)

        candidate_id = _candidate_id(target_feature, index)
        candidate_name = _field_value(target_feature, CANDIDATE_NAME_FIELD)
        for patch_type, margin in PATCH_SPECS:
            patch_feature = QgsFeature(output_layer.fields())
            patch_feature.setGeometry(_patch_geometry(geometry, patch_type, margin))
            patch_feature["patch_id"] = f"{candidate_id}_{patch_type}"
            patch_feature["candidate_id"] = candidate_id
            patch_feature["candidate_name"] = candidate_name
            patch_feature["patch_type"] = patch_type
            patch_feature["margin_m"] = margin if margin is not None else 0.0
            patch_feature["source_layer"] = target_layer.name()
            patch_feature["statut"] = "a_analyser"
            features.append(patch_feature)

    output_layer.dataProvider().addFeatures(features)
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

    saved_layer = QgsVectorLayer(
        f"{output_gpkg}|layername={OUTPUT_LAYER_NAME}",
        OUTPUT_LAYER_NAME,
        "ogr",
    )
    if saved_layer.isValid():
        project.addMapLayer(saved_layer)

    print(f"Couche source: {target_layer.name()}")
    print(f"Cibles lues: {target_layer.featureCount()}")
    print(f"Patchs generes: {len(features)}")
    print(f"Fichier cree: {output_gpkg}")
    print(f"Couche creee: {OUTPUT_LAYER_NAME}")


def _active_vector_layer():
    layer = iface.activeLayer()
    if layer is None or not isinstance(layer, QgsVectorLayer):
        raise ValueError("Selectionne d'abord la couche vectorielle contenant les 4 cibles.")
    if layer.geometryType() == QgsWkbTypes.NullGeometry:
        raise ValueError("La couche active ne contient pas de geometrie.")
    return layer


def _output_path():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return rf"{OUTPUT_DIR}\{OUTPUT_BASENAME}_{timestamp}.gpkg"


def _create_memory_layer(crs_authid):
    layer = QgsVectorLayer(f"Polygon?crs={crs_authid}", OUTPUT_LAYER_NAME, "memory")
    provider = layer.dataProvider()
    fields = QgsFields()
    fields.append(QgsField("patch_id", QVariant.String, len=80))
    fields.append(QgsField("candidate_id", QVariant.String, len=40))
    fields.append(QgsField("candidate_name", QVariant.String, len=120))
    fields.append(QgsField("patch_type", QVariant.String, len=40))
    fields.append(QgsField("margin_m", QVariant.Double))
    fields.append(QgsField("source_layer", QVariant.String, len=120))
    fields.append(QgsField("statut", QVariant.String, len=40))
    provider.addAttributes(fields)
    layer.updateFields()
    return layer


def _candidate_id(feature, fallback_index):
    value = _field_value(feature, CANDIDATE_ID_FIELD)
    if value:
        try:
            return f"candidat{int(float(value)):02d}"
        except ValueError:
            clean = _clean_identifier(value)
            return clean if clean.startswith("candidat") else f"candidat_{clean}"
    return f"candidat{fallback_index:02d}"


def _field_value(feature, field_name):
    if field_name not in feature.fields().names():
        return ""
    value = feature[field_name]
    return "" if value is None else str(value).strip()


def _clean_identifier(value):
    clean = []
    for char in value.lower():
        if char.isalnum():
            clean.append(char)
        elif char in {" ", "_", "-"}:
            clean.append("_")
    return "".join(clean).strip("_") or "sans_id"


def _extent_with_margin(extent, margin):
    rectangle = QgsRectangle(
        extent.xMinimum() - margin,
        extent.yMinimum() - margin,
        extent.xMaximum() + margin,
        extent.yMaximum() + margin,
    )
    return QgsGeometry.fromRect(rectangle)


def _patch_geometry(target_geometry, patch_type, margin):
    if patch_type == "patch" and QgsWkbTypes.geometryType(target_geometry.wkbType()) == QgsWkbTypes.PolygonGeometry:
        return QgsGeometry(target_geometry)
    effective_margin = margin if margin is not None else 25.0
    return _extent_with_margin(target_geometry.boundingBox(), effective_margin)


main()
