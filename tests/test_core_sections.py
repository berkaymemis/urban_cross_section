# -*- coding: utf-8 -*-
"""UrbanCrossSection — Core Birim Testleri (tests/test_core_sections.py)."""

import os
import sys
import unittest

# Eklenti kök dizinini ekle
plugin_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if plugin_root not in sys.path:
    sys.path.insert(0, plugin_root)

from core.elements import ElementType, SectionElement, BuildingFacade
from core.i18n import (
    get_language,
    set_language,
    retranslate_section_inplace,
    retranslate_profile_inplace,
)
from core.section_model import CrossSection
from core.presets import (
    ALL_PRESETS,
    list_presets,
    get_preset_by_width,
    get_preset_by_id,
)
from core.svg_exporter import SvgCrossSectionExporter
from core.profile_model import (
    UrbanProfile,
    BuildingMass,
    preset_profile_hillside_aa,
    preset_profile_slope_bb,
    pchip_interpolate_series,
)
from core.profile_svg import SvgUrbanProfileExporter


class TestUrbanCrossSectionCore(unittest.TestCase):
    """Core modellerinin ve algoritmalarının test sınıfı."""

    def test_section_element_creation_and_dict(self):
        elem = SectionElement(
            element_type=ElementType.SIDEWALK,
            width=2.50,
            label="Geniş Kaldırım",
            elevation=0.15,
            has_trees=True,
            pedestrian_count=2,
        )
        self.assertEqual(elem.width, 2.50)
        self.assertEqual(elem.element_type, ElementType.SIDEWALK)
        self.assertTrue(elem.has_trees)
        self.assertEqual(elem.pedestrian_count, 2)

        d = elem.to_dict()
        self.assertEqual(d["width"], 2.50)
        self.assertEqual(d["label"], "Geniş Kaldırım")

        # from_dict
        elem2 = SectionElement.from_dict(d)
        self.assertEqual(elem2.width, elem.width)
        self.assertEqual(elem2.label, elem.label)

    def test_building_facade(self):
        bldg = BuildingFacade(side="left", floors=5, floor_height=3.0, setback=4.0)
        self.assertEqual(bldg.total_height, 15.0)
        self.assertEqual(bldg.floors, 5)

        d = bldg.to_dict()
        bldg2 = BuildingFacade.from_dict(d)
        self.assertEqual(bldg2.total_height, 15.0)

    def test_cross_section_math_and_validation(self):
        sec = CrossSection(name="Test Yolu", right_of_way=10.0)
        sec.add_element(SectionElement(ElementType.SIDEWALK, 2.0))
        sec.add_element(SectionElement(ElementType.VEHICLE_LANE, 3.0))
        sec.add_element(SectionElement(ElementType.VEHICLE_LANE, 3.0))
        sec.add_element(SectionElement(ElementType.SIDEWALK, 2.0))

        self.assertEqual(sec.total_width, 10.0)
        self.assertEqual(sec.width_difference, 0.0)
        self.assertTrue(sec.is_balanced)

        stats = sec.summary_stats()
        self.assertEqual(stats["pedestrian_m"], 4.0)
        self.assertEqual(stats["vehicular_m"], 6.0)
        self.assertEqual(stats["pedestrian_pct"], 40.0)
        self.assertEqual(stats["vehicular_pct"], 60.0)

        val = sec.validate()
        self.assertTrue(val["valid"])
        self.assertEqual(len(val["errors"]), 0)

    def test_all_presets_balanced(self):
        """Tüm hazır şablonların toplam genişliği kendi right_of_way değerine eşit olmalıdır."""
        presets = list_presets()
        self.assertGreaterEqual(len(presets), 8)

        for p_info in presets:
            sec = get_preset_by_id(p_info["id"])
            diff = abs(sec.total_width - sec.right_of_way)
            self.assertLess(
                diff,
                0.05,
                f"Şablon '{sec.name}' dengeli değil! Toplam={sec.total_width}, Hedef={sec.right_of_way}",
            )
            val = sec.validate()
            self.assertTrue(val["valid"], f"Şablon '{sec.name}' doğrulama hatası verdi: {val['errors']}")

    def test_preset_by_width_matching(self):
        # 14.8 m arandığında 15m toplayıcı cadde şablonu dönmeli
        sec = get_preset_by_width(14.8)
        self.assertIsNotNone(sec)
        self.assertEqual(sec.right_of_way, 14.8)

    def test_svg_export(self):
        set_language("en")
        sec = get_preset_by_id("15m")
        exporter = SvgCrossSectionExporter(sec, pixels_per_meter=25.0)
        svg_str = exporter.export_svg()

        self.assertIn("<svg", svg_str)
        self.assertIn("</svg>", svg_str)
        self.assertIn("RIGHT-OF-WAY WIDTH", svg_str)
        self.assertIn("15.00 m", svg_str)
        # Ensure zero Turkish characters leak into default English SVG output
        for ch in "ğüşıöçİĞÜŞÖÇ":
            self.assertNotIn(ch, svg_str)

        # Write to disk check
        tmp_svg = os.path.join(plugin_root, "tests", "test_output.svg")
        try:
            exporter.save_to_file(tmp_svg)
            self.assertTrue(os.path.exists(tmp_svg))
            self.assertGreater(os.path.getsize(tmp_svg), 1000)
        finally:
            if os.path.exists(tmp_svg):
                os.remove(tmp_svg)

    def test_urban_profile_model(self):
        """1:1000 A-A' and B-B' urban profile model tests (100% EN default)."""
        set_language("en")
        prof_aa = preset_profile_hillside_aa()
        self.assertEqual(prof_aa.title, "1:1000 A-A' URBAN SECTION")
        self.assertEqual(prof_aa.total_length, 700.0)
        self.assertGreater(len(prof_aa.terrain_points), 10)
        self.assertGreater(len(prof_aa.buildings), 4)
        self.assertGreater(len(prof_aa.vegetation), 4)

        elev_100 = prof_aa.get_elevation_at(100.0)
        self.assertEqual(elev_100, 127.0)

        slopes = prof_aa.calculate_slopes()
        self.assertGreater(len(slopes), 2)

        prof_bb = preset_profile_slope_bb()
        self.assertEqual(prof_bb.title, "1:1000 B-B' URBAN SECTION")
        self.assertEqual(prof_bb.total_length, 450.0)

    def test_urban_profile_svg_export(self):
        """1:1000 A-A' urban profile SVG export test (100% EN default)."""
        set_language("en")
        prof = preset_profile_hillside_aa()
        exporter = SvgUrbanProfileExporter(prof)
        svg = exporter.render_to_svg(width_px=1200, height_px=400)
        self.assertIn("<svg", svg)
        self.assertIn("</svg>", svg)
        self.assertIn("1:1000 A-A' URBAN SECTION", svg)
        self.assertIn("skyGrad", svg)
        self.assertIn("soilHatch", svg)
        for ch in "ğüşıöçİĞÜŞÖÇ":
            self.assertNotIn(ch, svg)

    def test_bilingual_en_tr_preserves_geometry(self):
        """EN <-> TR language switching updates labels without altering geometry or utilities."""
        set_language("en")
        sec = get_preset_by_id("15m")
        orig_row = sec.right_of_way
        orig_widths = [e.width for e in sec.elements]
        self.assertIn("District Collector", sec.name)

        retranslate_section_inplace(sec, "tr")
        self.assertEqual(sec.language, "tr")
        self.assertIn("Bölge Toplayıcı", sec.name)
        self.assertEqual(sec.right_of_way, orig_row)
        self.assertEqual([e.width for e in sec.elements], orig_widths)
        svg_tr = SvgCrossSectionExporter(sec).export_svg()
        self.assertIn("KIRMIZI ÇİZGİ GENİŞLİĞİ", svg_tr)

        retranslate_section_inplace(sec, "en")
        self.assertEqual(sec.language, "en")
        self.assertIn("District Collector", sec.name)
        svg_en = SvgCrossSectionExporter(sec).export_svg()
        self.assertIn("RIGHT-OF-WAY WIDTH", svg_en)

        prof = preset_profile_hillside_aa("en")
        orig_pts = list(prof.terrain_points)
        retranslate_profile_inplace(prof, "tr")
        self.assertEqual(prof.title, "1/1000 A-A' KESİT")
        self.assertEqual(prof.terrain_points, orig_pts)
        retranslate_profile_inplace(prof, "en")
        self.assertEqual(prof.title, "1:1000 A-A' URBAN SECTION")
        set_language("en")


    def test_pchip_monotone_interpolation(self):
        """Eşyükselti eğrilerinden kot çıkarma için monoton kübik enterpolasyon testi."""
        # 5 adet eşyükselti eğrisi kesişimi
        contours = [(0.0, 100.0), (100.0, 110.0), (200.0, 120.0), (300.0, 130.0)]
        eval_x = [0.0, 50.0, 100.0, 150.0, 200.0, 250.0, 300.0]
        results = pchip_interpolate_series(contours, eval_x)
        self.assertEqual(len(results), len(eval_x))
        # Monoton artış kontrolü: her nokta bir öncekinden büyük veya eşit olmalı (asla geri çöküş yapmaz)
        for i in range(len(results) - 1):
            self.assertLessEqual(results[i][1], results[i + 1][1] + 1e-4)

    def test_urban_profile_statistics_and_slopes(self):
        """Topografik eğim ve istatistik analizi testi."""
        prof = preset_profile_hillside_aa()
        stats = prof.get_statistics()
        self.assertIn("min_elevation", stats)
        self.assertIn("max_elevation", stats)
        self.assertIn("elevation_delta", stats)
        self.assertIn("max_slope_pct", stats)
        self.assertIn("avg_slope_pct", stats)
        self.assertGreater(stats["elevation_delta"], 0.0)
        self.assertGreater(stats["max_slope_pct"], 0.0)

        # Yerel eğim sorgusu
        slope_100 = prof.get_slope_at(100.0)
        self.assertIsInstance(slope_100, float)

    def test_profile_building_clustering(self):
        """Uzun kesitlerde yakın binaların kentsel blok kütlesi halinde birleştirilmesi testi."""
        prof = UrbanProfile(total_length=2800.0)
        # 3 adet birbirine bitişik/yakın bina (10m aralıklı)
        prof.add_building(BuildingMass(start_dist=100.0, end_dist=120.0, ground_elevation=100.0, floors=3))
        prof.add_building(BuildingMass(start_dist=125.0, end_dist=140.0, ground_elevation=100.0, floors=4))
        prof.add_building(BuildingMass(start_dist=145.0, end_dist=160.0, ground_elevation=100.0, floors=5))
        # 1 adet uzakta tekil bina
        prof.add_building(BuildingMass(start_dist=600.0, end_dist=620.0, ground_elevation=105.0, floors=2))

        self.assertEqual(len(prof.buildings), 4)
        prof.cluster_buildings(max_gap=15.0, min_width=20.0)

        # 3 yakın bina tek bir kentsel blok olmalı, uzaktaki bina ayrı kalmalı -> toplam 2 kütle
        self.assertEqual(len(prof.buildings), 2)
        b1 = prof.buildings[0]
        self.assertEqual(b1.start_dist, 100.0)
        self.assertEqual(b1.end_dist, 160.0)
        self.assertEqual(b1.floors, 5)  # En yüksek kat sayısı korunmalı

    def test_profile_segmentation(self):
        """2800 metrelik uzun bir kesitin 700m'lik jüri paftalarına bölünmesi testi."""
        prof = UrbanProfile(total_length=2800.0)
        prof.add_building(BuildingMass(start_dist=200.0, end_dist=240.0, ground_elevation=100.0, floors=4))
        prof.add_building(BuildingMass(start_dist=900.0, end_dist=940.0, ground_elevation=105.0, floors=3))

        segs = prof.get_segments(segment_length=700.0)
        self.assertEqual(len(segs), 4)

        # Bölüm 1 (0 - 700m): İlk bina burada olmalı
        seg1 = segs[0]
        self.assertEqual(seg1.total_length, 700.0)
        self.assertEqual(len(seg1.buildings), 1)
        self.assertEqual(seg1.buildings[0].start_dist, 200.0)
        self.assertEqual(seg1.buildings[0].end_dist, 240.0)

        # Bölüm 2 (700 - 1400m): İkinci bina burada olmalı (900m - 700m = 200m bağıl konuma kaydırılmış)
        seg2 = segs[1]
        self.assertEqual(seg2.total_length, 700.0)
        self.assertEqual(len(seg2.buildings), 1)
        self.assertAlmostEqual(seg2.buildings[0].start_dist, 200.0, places=1)

    def test_underground_utilities_and_visual_options(self):
        """Yeraltı altyapı hatları ve görsel sunum seçeneklerinin yönetimi ve serileştirme testi."""
        sec = get_preset_by_id("15m")
        self.assertTrue(sec.has_water_pipe)
        self.assertFalse(sec.has_sewer_pipe)

        # Tuvalden veya panelden boru açma/kapama
        new_water = sec.toggle_utility("water")
        self.assertFalse(new_water)
        self.assertFalse(sec.has_water_pipe)

        new_sewer = sec.toggle_utility("sewer")
        self.assertTrue(new_sewer)
        self.assertTrue(sec.has_sewer_pipe)

        sec.visual_theme = "technical_cad"
        sec.show_slope_arrows = True
        d = sec.to_dict()
        sec_restored = CrossSection.from_dict(d)
        self.assertFalse(sec_restored.has_water_pipe)
        self.assertTrue(sec_restored.has_sewer_pipe)
        self.assertEqual(sec_restored.visual_theme, "technical_cad")

    def test_profile_cut_and_silhouette_separation(self):
        """Kesilen vs sokak silüeti kütlelerinin ayrı kümelenmesi, segmentasyonu ve istatistikleri."""
        prof = UrbanProfile(
            total_length=2800.0,
            look_direction="left",
            look_depth=25.0,
        )
        prof.terrain_points = [(0.0, 100.0), (1000.0, 108.0), (2800.0, 115.0)]
        prof._compute_slope_profile()

        # İki yakın kesilen bina (aralık 4m) -> birleşmeli, 2 silüet bina (aralık 4m) -> ayrı olarak birleşmeli
        # Kesilen ile silüet yatayda çakışsa dahi ASLA birbirine kaynaklanmamalı!
        prof.add_building(
            BuildingMass(
                start_dist=100.0,
                end_dist=120.0,
                ground_elevation=101.0,
                ground_min_elevation=99.5,
                floors=4,
                is_cut=True,
                depth_dist=0.0,
            )
        )
        prof.add_building(
            BuildingMass(
                start_dist=124.0,
                end_dist=144.0,
                ground_elevation=101.5,
                ground_min_elevation=100.0,
                floors=3,
                is_cut=True,
                depth_dist=0.0,
            )
        )
        prof.add_building(
            BuildingMass(
                start_dist=105.0,
                end_dist=125.0,
                ground_elevation=101.2,
                ground_min_elevation=99.8,
                floors=5,
                is_cut=False,
                depth_dist=12.5,
            )
        )
        prof.add_building(
            BuildingMass(
                start_dist=129.0,
                end_dist=150.0,
                ground_elevation=101.6,
                ground_min_elevation=100.2,
                floors=2,
                is_cut=False,
                depth_dist=18.0,
            )
        )

        stats_before = prof.get_statistics()
        self.assertEqual(stats_before["building_count"], 4)
        self.assertEqual(stats_before["cut_building_count"], 2)
        self.assertEqual(stats_before["silhouette_building_count"], 2)
        self.assertEqual(stats_before["look_direction"], "left")
        self.assertAlmostEqual(stats_before["look_depth"], 25.0)

        prof.cluster_buildings(max_gap=10.0, min_width=15.0)
        stats_after = prof.get_statistics()
        # 1 birleşik kesilen blok + 1 birleşik silüet blok = 2 ayrı blok
        self.assertEqual(stats_after["building_count"], 2)
        self.assertEqual(stats_after["cut_building_count"], 1)
        self.assertEqual(stats_after["silhouette_building_count"], 1)

        cut_blk = [b for b in prof.buildings if b.is_cut][0]
        sil_blk = [b for b in prof.buildings if not b.is_cut][0]
        self.assertAlmostEqual(cut_blk.ground_min_elevation, 99.5)
        self.assertAlmostEqual(sil_blk.depth_dist, 12.5)
        self.assertEqual(sil_blk.floors, 5)

        seg0 = prof.create_segment(0.0, 700.0)
        # 1/1000 bölümlemede birleşmemiş 4 ham bina korunur (2 kesilen + 2 silüet)
        self.assertEqual(len(seg0.buildings), 4)
        seg_sil = [b for b in seg0.buildings if not b.is_cut][0]
        self.assertAlmostEqual(seg_sil.depth_dist, 12.5)
        self.assertAlmostEqual(seg_sil.ground_min_elevation, 99.8)


if __name__ == "__main__":
    unittest.main()
