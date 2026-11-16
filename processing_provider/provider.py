# -*- coding: utf-8 -*-
"""UrbanCrossSection — Processing Provider (processing_provider/provider.py)."""

import os
from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon

from .algorithms import (
    GenerateCrossSectionLinesAlgorithm,
    BatchExportSectionsAlgorithm,
)


class UrbanCrossSectionProvider(QgsProcessingProvider):
    """QGIS Processing Araç Kutusu Sağlayıcısı."""

    def loadAlgorithms(self):
        self.addAlgorithm(GenerateCrossSectionLinesAlgorithm())
        self.addAlgorithm(BatchExportSectionsAlgorithm())

    def id(self):
        return "urbancrosssection"

    def name(self):
        return "Urban Cross-Section"

    def longName(self):
        return "UrbanCrossSection — Street & Urban Terrain Section Tools"

    def icon(self):
        icon_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "icons",
            "icon.png",
        )
        if os.path.exists(icon_path):
            return QIcon(icon_path)
        return QIcon()
