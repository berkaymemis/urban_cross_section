# -*- coding: utf-8 -*-
"""UrbanCrossSection — Kentsel Sokak ve Tipik Yol Enkesiti Çizim Motoru.

QGIS Eklenti Yükleyici Fabrika Fonksiyonu.
"""


def classFactory(iface):
    """QGIS eklenti fabrikası."""
    from .plugin import UrbanCrossSectionPlugin
    return UrbanCrossSectionPlugin(iface)
