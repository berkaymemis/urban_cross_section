# -*- coding: utf-8 -*-
"""UrbanCrossSection — Processing Toolbox Algorithms (processing_provider/algorithms.py)."""

import os
from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterVectorLayer,
    QgsProcessingParameterField,
    QgsProcessingParameterNumber,
    QgsProcessingParameterFolderDestination,
    QgsProcessingParameterFeatureSink,
    QgsProcessingOutputString,
    QgsProcessingException,
    QgsFeatureSink,
    QgsFields,
    QgsField,
    QgsFeature,
    QgsWkbTypes,
)
from qgis.PyQt.QtCore import QVariant

from ..core.presets import get_preset_by_width
from ..core.svg_exporter import SvgCrossSectionExporter
from ..gis.cross_line_gen import compute_perpendicular_line
from ..gis.layer_reader import parse_road_width


class GenerateCrossSectionLinesAlgorithm(QgsProcessingAlgorithm):
    """Generates perpendicular cross-section lines along road centerlines."""

    INPUT_LAYER = "INPUT_LAYER"
    WIDTH_FIELD = "WIDTH_FIELD"
    DEFAULT_WIDTH = "DEFAULT_WIDTH"
    OUTPUT = "OUTPUT"

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.INPUT_LAYER,
                "Input Road Layer (Line)",
                [QgsProcessing.SourceType.TypeVectorLine],
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.WIDTH_FIELD,
                "Road Width Field (Optional)",
                parentLayerParameterName=self.INPUT_LAYER,
                type=QgsProcessingParameterField.DataType.Any,
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.DEFAULT_WIDTH,
                "Default Road Width (m)",
                type=QgsProcessingParameterNumber.Type.Double,
                defaultValue=15.0,
                minValue=2.0,
                maxValue=120.0,
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                "Perpendicular Section Lines",
                QgsProcessing.SourceType.TypeVectorLine,
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        layer = self.parameterAsVectorLayer(parameters, self.INPUT_LAYER, context)
        if not layer or not layer.isValid():
            raise QgsProcessingException("Valid input line layer is required.")
        width_field = self.parameterAsString(parameters, self.WIDTH_FIELD, context)
        default_w = self.parameterAsDouble(parameters, self.DEFAULT_WIDTH, context)

        fields = QgsFields()
        fields.append(QgsField("section_id", QVariant.String, len=10))
        fields.append(QgsField("road_width", QVariant.Double))
        fields.append(QgsField("source_fid", QVariant.LongLong))

        (sink, dest_id) = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            fields,
            QgsWkbTypes.Type.LineString,
            layer.crs(),
        )

        total = layer.featureCount()
        count = 0

        for i, feat in enumerate(layer.getFeatures()):
            if feedback.isCanceled():
                break

            geom = feat.geometry()
            if not geom or geom.isEmpty():
                continue

            w = default_w
            if width_field and width_field in feat.fields().names():
                parsed = parse_road_width(feat[width_field])
                if parsed:
                    w = parsed

            perp_geom = compute_perpendicular_line(geom, right_of_way=w, fraction=0.5)
            if perp_geom:
                out_feat = QgsFeature(fields)
                out_feat.setGeometry(perp_geom)
                out_feat.setAttribute("section_id", f"S-{count + 1}")
                out_feat.setAttribute("road_width", float(w))
                out_feat.setAttribute("source_fid", feat.id())
                sink.addFeature(out_feat, QgsFeatureSink.Flag.FastInsert)
                count += 1

            if total > 0:
                feedback.setProgress(int((i / total) * 100))

        feedback.pushInfo(f"Generated {count} perpendicular cross-section lines.")
        return {self.OUTPUT: dest_id}

    def name(self):
        return "generate_cross_sections"

    def displayName(self):
        return "Generate Perpendicular Section Lines"

    def group(self):
        return "Street & Cross-Section Tools"

    def groupId(self):
        return "road_cross_sections"

    def createInstance(self):
        return GenerateCrossSectionLinesAlgorithm()


class BatchExportSectionsAlgorithm(QgsProcessingAlgorithm):
    """Exports architectural vector SVG street sections for each unique road width."""

    INPUT_LAYER = "INPUT_LAYER"
    WIDTH_FIELD = "WIDTH_FIELD"
    OUTPUT_FOLDER = "OUTPUT_FOLDER"
    EXPORT_SUMMARY = "EXPORT_SUMMARY"

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.INPUT_LAYER,
                "Input Road Layer (Line)",
                [QgsProcessing.SourceType.TypeVectorLine],
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.WIDTH_FIELD,
                "Road Width Field",
                parentLayerParameterName=self.INPUT_LAYER,
                type=QgsProcessingParameterField.DataType.Any,
            )
        )
        self.addParameter(
            QgsProcessingParameterFolderDestination(
                self.OUTPUT_FOLDER,
                "Output Folder for SVG Sections",
            )
        )
        self.addOutput(
            QgsProcessingOutputString(
                self.EXPORT_SUMMARY,
                "Export Summary",
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        layer = self.parameterAsVectorLayer(parameters, self.INPUT_LAYER, context)
        if not layer or not layer.isValid():
            raise QgsProcessingException("Valid input line layer is required.")
        width_field = self.parameterAsString(parameters, self.WIDTH_FIELD, context)
        out_folder = self.parameterAsString(parameters, self.OUTPUT_FOLDER, context)
        os.makedirs(out_folder, exist_ok=True)

        unique_widths = set()
        for feat in layer.getFeatures():
            val = parse_road_width(feat[width_field])
            if val:
                unique_widths.add(round(val, 1))

        feedback.pushInfo(f"Detected unique road widths: {sorted(list(unique_widths))} m")

        exported_files = []
        for w in sorted(list(unique_widths)):
            sec = get_preset_by_width(w, lang="en")
            filename = f"Street_Section_{w:.1f}m.svg".replace(".", "_") + ".svg"
            out_path = os.path.join(out_folder, filename)
            exporter = SvgCrossSectionExporter(sec)
            exporter.save_to_file(out_path)
            exported_files.append(out_path)
            feedback.pushInfo(f"Exported: {filename}")

        summary = f"Exported {len(exported_files)} unique street cross-section SVG files."
        return {
            self.OUTPUT_FOLDER: out_folder,
            self.EXPORT_SUMMARY: summary,
        }

    def name(self):
        return "batch_export_sections"

    def displayName(self):
        return "Batch Export Vector Sections (SVG)"

    def group(self):
        return "Street & Cross-Section Tools"

    def groupId(self):
        return "road_cross_sections"

    def createInstance(self):
        return BatchExportSectionsAlgorithm()
