# -*- coding: utf-8 -*-
"""UrbanCrossSection — QGIS Eklenti Ana Giriş Noktası (plugin.py).

Resmi QGIS 3 ve QGIS 4 (Qt5/Qt6) uyumlu, 2026 Hub standartlarında eklenti sınıfı.
"""

import os
from qgis.core import QgsApplication
from qgis.PyQt.QtGui import QIcon

from .gis.compat import QAction
from .ui.main_dialog import UrbanCrossSectionDialog
from .processing_provider.provider import UrbanCrossSectionProvider


class UrbanCrossSectionPlugin:
    """UrbanCrossSection QGIS Eklentisi."""

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.actions = []
        self.menu = "&UrbanCrossSection"
        self.provider = None
        self.dialog = None

    def initProcessing(self):
        """Processing Araç Kutusu sağlayıcısını kaydeder."""
        self.provider = UrbanCrossSectionProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def initGui(self):
        """Arayüz menü öğelerini ve araç çubuğu ikonunu oluşturur."""
        self.initProcessing()

        icon_path = os.path.join(self.plugin_dir, "icons", "icon.png")
        icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()

        self.action = QAction(
            icon,
            "UrbanCrossSection — Street & 1:1000 Cross-Section Studio",
            self.iface.mainWindow() if self.iface else None,
        )
        self.action.setToolTip("Interactive street cross-section designer and 1:1000 urban elevation profile studio")
        self.action.triggered.connect(self.run)

        if self.iface:
            self.iface.addPluginToMenu(self.menu, self.action)
            self.iface.addToolBarIcon(self.action)

        self.actions.append(self.action)

    def unload(self):
        """Eklenti kaldırılırken veya yeniden yüklenirken tüm menü ve sağlayıcıları temizler."""
        if self.provider:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None

        if self.iface:
            for action in self.actions:
                self.iface.removePluginMenu(self.menu, action)
                self.iface.removeToolBarIcon(action)
        self.actions.clear()

        if self.dialog:
            self.dialog.close()
            self.dialog = None

    def run(self):
        """Ana diyalog penceresini açar."""
        parent = self.iface.mainWindow() if self.iface else None
        if not self.dialog:
            self.dialog = UrbanCrossSectionDialog(iface=self.iface, parent=parent)
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()
