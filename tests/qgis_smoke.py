# -*- coding: utf-8 -*-
"""UrbanCrossSection — Headless QGIS Duman Testi (tests/qgis_smoke.py).

QGIS 3 (Qt5) ve QGIS 4 (Qt6) dual-runtime ortamlarında tam kapsamlı test.
"""

import os
import sys

# Platform offscreen (başsız testler için)
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from qgis.core import (
    QgsApplication,
    QgsProject,
    QgsGeometry,
    QgsPointXY,
    QgsRectangle,
)


def main():
    qgs = QgsApplication([], True)
    qgs.initQgis()
    try:
        plugin_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        parent_dir = os.path.dirname(plugin_root)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        if plugin_root not in sys.path:
            sys.path.insert(0, plugin_root)

        # 1. Plugin Sınıfı Testi
        from urban_cross_section.plugin import UrbanCrossSectionPlugin
        plugin = UrbanCrossSectionPlugin(iface=None)
        assert plugin is not None
        plugin.initProcessing()
        assert plugin.provider is not None

        # 2. Processing Provider ve Algoritmaları
        from urban_cross_section.processing_provider.provider import UrbanCrossSectionProvider
        prov = UrbanCrossSectionProvider()
        prov.loadAlgorithms()
        alg_count = len(prov.algorithms())
        assert alg_count >= 2, f"En az 2 algoritma bekleniyordu, {alg_count} bulundu"

        # 3. Main Studio Dialog (Basic Mode + 100% English Default + Advanced + EN/TR Check)
        from urban_cross_section.ui.main_dialog import UrbanCrossSectionDialog
        from urban_cross_section.core.i18n import get_language
        dlg = UrbanCrossSectionDialog(iface=None)
        assert dlg is not None
        assert dlg.canvas is not None
        assert dlg.current_section is not None
        assert dlg.current_section.right_of_way == 15.0
        assert get_language() == "en"
        assert not dlg.is_advanced_mode
        assert dlg.prof_adv_gis_widget.isHidden()
        assert dlg.prof_insp_frame.isHidden()
        assert dlg.utility_drawer.isHidden()
        for ch in "ğüşıöçİĞÜŞÖÇ":
            assert ch not in dlg.windowTitle(), f"Turkish char leaked into EN title: {dlg.windowTitle()}"
            assert ch not in dlg.main_tabs.tabText(0)
            assert ch not in dlg.main_tabs.tabText(1)

        # Switch to Advanced Mode and verify controls expand cleanly
        dlg.set_advanced_mode(True)
        assert dlg.is_advanced_mode
        assert not dlg.prof_adv_gis_widget.isHidden()
        assert not dlg.prof_insp_frame.isHidden()

        # Switch language to TR and back to EN without changing geometry
        prev_row = dlg.current_section.right_of_way
        dlg.set_ui_language("tr")
        assert get_language() == "tr"
        assert dlg.current_section.right_of_way == prev_row
        assert "Sokak" in dlg.main_tabs.tabText(0)
        dlg.set_ui_language("en")
        assert get_language() == "en"
        assert dlg.current_section.right_of_way == prev_row
        dlg.set_advanced_mode(False)

        # Şablon değiştirme testi
        dlg.combo_presets.setCurrentIndex(0)  # 7m
        assert dlg.current_section.right_of_way == 7.0

        # Mod 2: 1/1000 Kentsel Silüet ve Topografya Kesiti Testi
        assert dlg.profile_canvas is not None
        assert dlg.current_profile is not None
        assert "A-A'" in dlg.current_profile.title
        dlg.combo_profile_presets.setCurrentIndex(1)  # B-B'
        assert "B-B'" in dlg.current_profile.title

        # Haritadan A-B örnekleme testi
        from urban_cross_section.gis.profile_sampler import (
            sample_profile_between_points,
            sample_profile_from_dem,
            sample_profile_from_contours,
            parse_floor_count,
        )
        assert parse_floor_count("Z+3") == 4
        assert parse_floor_count("4 Kat") == 4
        assert parse_floor_count("3,0") == 3
        sampled = sample_profile_between_points(
            QgsPointXY(500000.0, 4200000.0),
            QgsPointXY(500600.0, 4200400.0),
            title="1/1000 C-C' KESİT",
        )
        assert sampled is not None
        assert sampled.total_length > 100.0
        assert len(sampled.terrain_points) > 20
        assert len(sampled.buildings) > 0

        # Gerçek Yerel Veri Testi (DEM, Eğim ve Eşyükselti)
        from qgis.core import QgsRasterLayer, QgsVectorLayer
        dem_file = r"c:\qgis_plugin\veri\dem_yukseklik.tif"
        slope_file = r"c:\qgis_plugin\veri\egim_yuzde.tif"
        contour_file = r"c:\qgis_plugin\veri\esyukselti_egrileri.gpkg"

        if os.path.exists(dem_file):
            r_dem = QgsRasterLayer(dem_file, "dem_yukseklik")
            assert r_dem.isValid()
            QgsProject.instance().addMapLayer(r_dem)

            # DEM üzerinden örnekleme
            pt_start = QgsPointXY(560000.0, 4218000.0)
            pt_end = QgsPointXY(560700.0, 4218000.0)
            prof_dem = sample_profile_between_points(
                pt_start,
                pt_end,
                title="1/1000 DEM KESİT",
                source_mode="dem",
                dem_layer=r_dem,
            )
            assert prof_dem is not None
            assert prof_dem.total_length == 700.0
            assert prof_dem.min_elevation > 20.0
            assert prof_dem.max_elevation < 1200.0
            stats_dem = prof_dem.get_statistics()
            assert stats_dem["max_slope_pct"] > 0.0

        if os.path.exists(contour_file):
            v_cnt = QgsVectorLayer(contour_file, "esyukselti_egrileri", "ogr")
            assert v_cnt.isValid()
            QgsProject.instance().addMapLayer(v_cnt)

            prof_cnt = sample_profile_between_points(
                QgsPointXY(560000.0, 4218000.0),
                QgsPointXY(560700.0, 4218000.0),
                title="1/1000 EŞYÜKSELTİ KESİT",
                source_mode="contours",
                contour_layer=v_cnt,
                contour_elev_field="kot",
            )
            assert prof_cnt is not None
            assert len(prof_cnt.terrain_points) > 20

        # Yol katmanı kesişim ve KeyError güvenliği testi
        from qgis.core import QgsField, QgsFeature
        from qgis.PyQt.QtCore import QVariant
        mem_road = QgsVectorLayer("LineString?crs=epsg:32635", "test_yol", "memory")
        pr = mem_road.dataProvider()
        pr.addAttributes([QgsField("kaplama_turu", QVariant.String)])
        mem_road.updateFields()
        f_rd = QgsFeature(mem_road.fields())
        f_rd.setGeometry(QgsGeometry.fromPolylineXY([
            QgsPointXY(560300.0, 4217900.0),
            QgsPointXY(560300.0, 4218100.0),
        ]))
        f_rd["kaplama_turu"] = "Asfalt"
        pr.addFeatures([f_rd])
        assert mem_road.featureCount() == 1

        prof_road_test = sample_profile_between_points(
            QgsPointXY(560000.0, 4218000.0),
            QgsPointXY(560700.0, 4218000.0),
            title="1/1000 Yol Test",
            road_layer=mem_road,
        )
        assert prof_road_test is not None
        assert len(prof_road_test.roads) >= 1
        assert prof_road_test.roads[0].name == "Street"

        # Sokak Koridoru Bakış Yönü + Gerçek Bina Katmanı (Sahte Bina Yok) Testi
        mem_bldg = QgsVectorLayer("Polygon?crs=epsg:32635", "test_bina", "memory")
        pr_b = mem_bldg.dataProvider()
        pr_b.addAttributes([QgsField("ZEMINUSTUKATSAYISI", QVariant.String)])
        mem_bldg.updateFields()
        f_north = QgsFeature(mem_bldg.fields())
        f_north.setGeometry(QgsGeometry.fromRect(QgsRectangle(560100.0, 4218008.0, 560140.0, 4218022.0)))
        f_north["ZEMINUSTUKATSAYISI"] = "Z+3"
        f_south = QgsFeature(mem_bldg.fields())
        f_south.setGeometry(QgsGeometry.fromRect(QgsRectangle(560220.0, 4217978.0, 560255.0, 4217992.0)))
        f_south["ZEMINUSTUKATSAYISI"] = "2"
        pr_b.addFeatures([f_north, f_south])

        # Sol taraf (kuzey): sadece Z+3 (4 katlı) bina silüete girmeli, hayalî ağaç olmamalı
        prof_left = sample_profile_between_points(
            QgsPointXY(560000.0, 4218000.0),
            QgsPointXY(560350.0, 4218000.0),
            building_layer=mem_bldg,
            building_floors_field="ZEMINUSTUKATSAYISI",
            look_mode="left",
            look_depth=25.0,
            auto_detect_layers=False,
            include_placeholder_trees=False,
        )
        assert len(prof_left.buildings) == 1, f"1 sol cephe binası bekleniyordu, {len(prof_left.buildings)} bulundu"
        assert prof_left.buildings[0].floors == 4
        assert prof_left.buildings[0].is_cut is False
        assert len(prof_left.vegetation) == 0

        # Sadece kesilen modunda sokak ortasındaki çizgi hiç bina kesmez -> 0 bina (sahte kütle yok!)
        prof_cut_only = sample_profile_between_points(
            QgsPointXY(560000.0, 4218000.0),
            QgsPointXY(560350.0, 4218000.0),
            building_layer=mem_bldg,
            building_floors_field="ZEMINUSTUKATSAYISI",
            look_mode="cut_only",
            look_depth=25.0,
            auto_detect_layers=False,
            include_placeholder_trees=False,
        )
        assert len(prof_cut_only.buildings) == 0, "Sadece kesilen modda sokak ortası 0 bina döndürmelidir!"

        # Dialog Topografya Katman Yenileme Testi
        dlg._refresh_topography_layers()
        dlg.combo_exag.setCurrentIndex(1)  # 2x Abartı
        assert dlg.current_profile.vertical_exaggeration == 2.0

        # 4. SVG & 300 DPI PNG Export Tests (Street + Profile Canvas)
        tmp_dir = os.path.join(plugin_root, "tests")
        tmp_svg = os.path.join(tmp_dir, "smoke_test.svg")
        tmp_png = os.path.join(tmp_dir, "smoke_street.png")
        tmp_prof_svg = os.path.join(tmp_dir, "smoke_profile.svg")
        tmp_prof_png = os.path.join(tmp_dir, "smoke_profile.png")
        from urban_cross_section.core.svg_exporter import SvgCrossSectionExporter
        from urban_cross_section.core.profile_svg import SvgUrbanProfileExporter
        exporter = SvgCrossSectionExporter(dlg.current_section)
        exporter.save_to_file(tmp_svg)
        assert os.path.exists(tmp_svg)
        assert os.path.getsize(tmp_svg) > 500
        dlg.canvas.export_to_image(tmp_png, dpi=150)
        assert os.path.exists(tmp_png) and os.path.getsize(tmp_png) > 1000
        SvgUrbanProfileExporter(dlg.current_profile).save_to_file(tmp_prof_svg)
        assert os.path.exists(tmp_prof_svg) and os.path.getsize(tmp_prof_svg) > 500
        dlg.profile_canvas.export_to_image(tmp_prof_png, dpi=150)
        assert os.path.exists(tmp_prof_png) and os.path.getsize(tmp_prof_png) > 1000

        # 5. Perpendicular Map Section Line Tests (Single + Multipart LineString)
        from urban_cross_section.gis.cross_line_gen import add_cross_section_to_map, compute_perpendicular_line
        test_line = QgsGeometry.fromPolylineXY([
            QgsPointXY(500000.0, 4200000.0),
            QgsPointXY(500100.0, 4200000.0),
        ])
        feat = add_cross_section_to_map(
            road_geometry=test_line,
            right_of_way=15.0,
            label="A - A'",
            road_name="Main Avenue",
        )
        assert feat is not None
        assert feat.geometry() is not None
        assert not feat.geometry().isEmpty()
        multi_line = QgsGeometry.fromMultiPolylineXY([
            [QgsPointXY(500000.0, 4200000.0), QgsPointXY(500100.0, 4200000.0)],
            [QgsPointXY(500120.0, 4200000.0), QgsPointXY(500160.0, 4200000.0)],
        ])
        perp_multi = compute_perpendicular_line(multi_line, right_of_way=12.0)
        assert perp_multi is not None and not perp_multi.isEmpty()

        # 6. Processing Toolbox Execution Tests
        from qgis.core import QgsProcessingContext, QgsProcessingFeedback
        mem_proc_road = QgsVectorLayer("LineString?crs=epsg:32635", "proc_road", "memory")
        pr_p = mem_proc_road.dataProvider()
        pr_p.addAttributes([QgsField("width", QVariant.String)])
        mem_proc_road.updateFields()
        f_pr = QgsFeature(mem_proc_road.fields())
        f_pr.setGeometry(QgsGeometry.fromPolylineXY([
            QgsPointXY(560000.0, 4218000.0),
            QgsPointXY(560100.0, 4218000.0),
        ]))
        f_pr["width"] = "15 m"
        pr_p.addFeatures([f_pr])

        p_ctx = QgsProcessingContext()
        p_fb = QgsProcessingFeedback()
        alg_gen = QgsApplication.processingRegistry().algorithmById("urbancrosssection:generate_cross_sections")
        assert alg_gen is not None
        res_gen, ok_gen = alg_gen.run(
            {"INPUT_LAYER": mem_proc_road, "WIDTH_FIELD": "width", "DEFAULT_WIDTH": 15.0, "OUTPUT": "memory:"},
            p_ctx,
            p_fb,
        )
        assert ok_gen and res_gen.get("OUTPUT") is not None

        tmp_batch_dir = os.path.join(tmp_dir, "smoke_batch_svg")
        alg_batch = QgsApplication.processingRegistry().algorithmById("urbancrosssection:batch_export_sections")
        assert alg_batch is not None
        res_batch, ok_batch = alg_batch.run(
            {"INPUT_LAYER": mem_proc_road, "WIDTH_FIELD": "width", "OUTPUT_FOLDER": tmp_batch_dir},
            p_ctx,
            p_fb,
        )
        assert ok_batch and os.path.isdir(tmp_batch_dir)
        batch_svgs = [f for f in os.listdir(tmp_batch_dir) if f.endswith(".svg")]
        assert len(batch_svgs) == 1

        # 7. QGIS Print Layout Insertion Test
        from urban_cross_section.gis.layout_inserter import insert_section_image_to_layout
        pic_item = insert_section_image_to_layout(
            image_path=tmp_svg,
            layout_name="Test Layout",
            x_mm=10.0,
            y_mm=10.0,
            width_mm=150.0,
            height_mm=75.0,
        )
        assert pic_item is not None

        # Cleanup temporary outputs
        import shutil
        for p in (tmp_svg, tmp_png, tmp_prof_svg, tmp_prof_png):
            if os.path.exists(p):
                os.remove(p)
        if os.path.isdir(tmp_batch_dir):
            shutil.rmtree(tmp_batch_dir, ignore_errors=True)

        plugin.unload()

        print("URBAN_CROSS_SECTION_SMOKE_OK")
        return 0
    finally:
        qgs.exitQgis()


if __name__ == "__main__":
    sys.exit(main())
