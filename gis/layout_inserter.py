# -*- coding: utf-8 -*-
"""UrbanCrossSection — QGIS Print Layout (Baskı Düzeni / Jüri Paftası) Entegrasyonu (gis/layout_inserter.py)."""

import os
from qgis.core import (
    QgsProject,
    QgsPrintLayout,
    QgsLayoutItemPicture,
    QgsLayoutPoint,
    QgsLayoutSize,
    QgsUnitTypes,
)


def get_available_layouts(project=None):
    """Projedeki mevcut tüm QGIS Baskı Düzenlerinin (Print Layouts) listesini döner."""
    prj = project or QgsProject.instance()
    layouts = prj.layoutManager().printLayouts()
    return [(layout.name(), layout) for layout in layouts]


def get_or_create_layout(layout_name="Urban Cross-Sections Layout", project=None):
    """Belirtilen isimdeki baskı düzenini bulur veya A3 yatay yeni bir pafta üretir."""
    prj = project or QgsProject.instance()
    layout_mgr = prj.layoutManager()

    existing = layout_mgr.layoutByName(layout_name)
    if existing and isinstance(existing, QgsPrintLayout):
        return existing

    # Yeni A3 Yatay Düzen Oluştur
    layout = QgsPrintLayout(prj)
    layout.initializeDefaults()
    layout.setName(layout_name)

    # A3 Yatay Sayfa Boyutu (420 x 297 mm)
    page = layout.pageCollection().pages()[0]
    page.setPageSize(QgsLayoutSize(420, 297, QgsUnitTypes.LayoutMillimeters))

    layout_mgr.addLayout(layout)
    return layout


def insert_section_image_to_layout(
    image_path,
    layout=None,
    layout_name="Urban Cross-Sections Layout",
    x_mm=20.0,
    y_mm=20.0,
    width_mm=180.0,
    height_mm=90.0,
    project=None,
):
    """Insert an SVG or PNG cross-section graphic into the chosen QGIS Print Layout."""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Section graphic not found: {image_path}")

    target_layout = layout or get_or_create_layout(layout_name=layout_name, project=project)

    picture_item = QgsLayoutItemPicture(target_layout)
    picture_item.setPicturePath(image_path)

    # Konum ve boyut (Milimetre cinsinden)
    picture_item.attemptMove(QgsLayoutPoint(float(x_mm), float(y_mm), QgsUnitTypes.LayoutMillimeters))
    picture_item.attemptResize(QgsLayoutSize(float(width_mm), float(height_mm), QgsUnitTypes.LayoutMillimeters))

    target_layout.addLayoutItem(picture_item)
    return picture_item
