# -*- coding: utf-8 -*-
"""UrbanCrossSection — Pure Python Bilingual Dictionary & Localization (core/i18n.py).

Zero qgis or PyQt dependencies.
Default language is 100% English ("en"), with optional Turkish ("tr") toggle.
"""

from typing import Dict, Optional

DEFAULT_LANG = "en"
SUPPORTED_LANGS = ("en", "tr")
_ACTIVE_LANG = DEFAULT_LANG


def normalize_lang(lang: Optional[str]) -> str:
    """Normalize language code to 'en' or 'tr'."""
    if isinstance(lang, str) and lang.strip().lower().startswith("tr"):
        return "tr"
    return "en"


def get_language() -> str:
    """Return active plugin language ('en' by default)."""
    return _ACTIVE_LANG


def set_language(lang: str) -> str:
    """Set active plugin language globally and return normalized code."""
    global _ACTIVE_LANG
    _ACTIVE_LANG = normalize_lang(lang)
    return _ACTIVE_LANG


STRINGS: Dict[str, Dict[str, str]] = {
    "en": {
        # App / Header
        "window_title": "UrbanCrossSection — Street & 1:1000 Cross-Section Studio",
        "brand_html": (
            "<b>UrbanCrossSection</b> "
            "<span style='color:#64748b;font-size:11px;'>| Street &amp; Urban Profile Engine</span>"
        ),
        "mode_label": "Mode:",
        "mode_basic": "Basic",
        "mode_advanced": "Advanced",
        "mode_tooltip": "Basic shows essential controls only; Advanced reveals all GIS, utility & massing options.",
        "lang_label": "Lang:",
        "btn_collapse": "Map View",
        "btn_expand": "Expand Studio",
        "mini_pick_init": "Click Point A then Point B on the map...",
        "mini_pick_a": "Click start point (A) on the map canvas...",
        "mini_pick_b": "Point A set ({x:.1f}, {y:.1f}). Click end point (B)...",
        "mini_calculating": "Computing cross-section...",
        "mini_look": "Look:",
        "mini_expand": "Expand",
        "mini_cancel": "Cancel",
        "tab_street": "Street Cross-Section",
        "tab_profile": "1:1000 Urban Profile (A-B)",

        # Tab 1 Controls
        "lbl_template": "Template:",
        "lbl_road_name": "Street Name:",
        "lbl_corridor_width": "Width (m):",
        "lbl_theme": "Style:",
        "btn_read_map_road": "Read Map Road",
        "theme_architectural": "Architectural (Color)",
        "theme_technical_cad": "Technical CAD (Mono)",
        "theme_sunset_warm": "Warm Studio",
        "theme_night_lighting": "Night Lighting",
        "status_balanced": (
            "BALANCED (1:100): Strips {tot:.2f} m = Right-of-Way {row:.2f} m  |  "
            "Pedestrian/Green: {ped}%  |  Vehicle/Parking: {veh}%  |  Cycling: {cyc}%"
        ),
        "status_narrow": (
            "UNDER TARGET: Corridor {row:.2f} m, Strips {tot:.2f} m "
            "(+{diff:.2f} m spare) — add or widen a strip"
        ),
        "status_over": (
            "EXCEEDS CORRIDOR: Strips ({tot:.2f} m) exceed Right-of-Way ({row:.2f} m) "
            "by {over:.2f} m — narrow strips"
        ),
        "lbl_selected_prefix": "Selected:",
        "btn_move_left": "< Left",
        "btn_move_right": "Right >",
        "btn_delete": "Delete",
        "chk_trees": "Trees",
        "chk_lighting": "Lighting",
        "chk_bench": "Bench",
        "chk_bus_shelter": "Bus Shelter",
        "chk_tactile": "Tactile",
        "chk_bike_rack": "Bike Rack",
        "lbl_vehicle": "Vehicle:",
        "veh_none": "None",
        "veh_car": "Car",
        "veh_bus": "Bus",
        "lbl_people": "People:",
        "lbl_add_strip": "Add Strip:",
        "btn_utilities_show": "Utilities & Layers v",
        "btn_utilities_hide": "Utilities & Layers ^",
        "btn_buildings_show": "Side Buildings v",
        "btn_buildings_hide": "Side Buildings ^",

        # Palette items
        "pal_sidewalk": "Sidewalk (2.0m)",
        "pal_landscape": "Green Verge (1.5m)",
        "pal_bike": "Bike Lane (1.5m)",
        "pal_vehicle": "Car Lane (3.25m)",
        "pal_bus": "Bus Lane (3.5m)",
        "pal_parking": "Parking (2.0m)",
        "pal_median": "Median (2.0m)",
        "pal_tram": "Tramway (6.0m)",
        "pal_parklet": "Parklet (3.0m)",
        "pal_buffer": "Curb Buffer (0.5m)",

        # Utilities & Visual Layers Drawer
        "lbl_utilities": "Utilities:",
        "chk_util_water": "Water (DN200)",
        "chk_util_telecom": "Fiber (DN110)",
        "chk_util_power": "Power (DN125)",
        "chk_util_gas": "Gas (DN100)",
        "chk_util_drainage": "Storm (DN400)",
        "chk_util_sewer": "Sewer (DN600)",
        "chk_util_gallery": "Utility Gallery",
        "tip_util_gallery": "Combines water, fiber and power lines inside a single reinforced concrete box culvert.",
        "btn_util_all": "All On",
        "btn_util_none": "Clear All",
        "lbl_visual_layers": "Layers:",
        "chk_show_subgrade": "Subgrade Layers",
        "chk_show_buildings": "Side Buildings",
        "chk_show_slopes": "2% Cross-Slopes",
        "chk_show_cards": "Top Lane Cards",
        "chk_show_dimensions": "Dimensions",

        # Surrounding buildings drawer
        "lbl_left_floors": "Left Floors:",
        "lbl_right_floors": "Right Floors:",
        "lbl_setback": "Setback (m):",
        "lbl_sign": "Shop Sign:",

        # Tab 1 Actions
        "btn_map_line": "Add Section Line to Map",
        "btn_print_layout": "Add to Print Layout",
        "btn_export_svg": "Export SVG",
        "btn_export_png": "Export PNG (300 DPI)",
        "btn_close": "Close",

        # Tab 2 Controls
        "lbl_profile_preset": "Sample Profile:",
        "prof_preset_aa": "1:1000 A-A' Urban Hill & Slope (700m)",
        "prof_preset_bb": "1:1000 B-B' Continuous Slope & Valley (450m)",
        "lbl_title": "Title:",
        "lbl_sky": "Sky:",
        "sky_sunset": "Sunset",
        "sky_golden_hour": "Golden Hour",
        "sky_daylight": "Clear Sky (Day)",
        "lbl_exag": "Vertical Scale:",
        "exag_1": "1x (True 1:1)",
        "exag_2": "2x Exaggeration",
        "exag_3": "3x Exaggeration",
        "exag_5": "5x Exaggeration",
        "exag_10": "10x Exaggeration",
        "lbl_segment": "1:1000 Sheet Segment:",
        "btn_prev_seg": "< Prev Sheet",
        "btn_next_seg": "Next Sheet >",
        "btn_export_all_segs": "Export All Sheets (SVG)",
        "seg_single": "Single Sheet ({len:.1f} m)",
        "seg_overview": "Full Corridor Overview ({len:.1f} m)",
        "seg_item": "Sheet {idx}/{total} ({s}m - {e}m | {cnt} Masses)",

        "box_topo_title": "Terrain, Elevation & Building Source",
        "lbl_source_mode": "Source:",
        "mode_dem": "DEM Elevation Raster",
        "mode_contours": "Vector Contours",
        "mode_dem_slope": "DEM + Slope Raster",
        "mode_preset": "Demo Slope (Sample)",
        "lbl_dem": "DEM:",
        "lbl_terrain_layer": "Elevation:",
        "btn_load_dem": "DEM TIF...",
        "lbl_slope": "Slope (%):",
        "btn_load_slope": "Slope TIF...",
        "lbl_contour": "Contours:",
        "btn_load_contour": "Contours...",
        "lbl_elev_field": "Elev Field:",
        "lbl_bldg_layer": "Buildings:",
        "item_none_bldg": "None (No Polygon Layer)",
        "item_none_slope": "None (Compute from DEM)",
        "item_none_road": "None (No Road Layer)",
        "lbl_floors_field": "Floors Field:",
        "lbl_step": "Step:",
        "lbl_look": "Look Direction:",
        "look_auto": "Auto (Left / Opposite)",
        "look_left": "Left Side (A->B Left)",
        "look_right": "Right Side (A->B Right)",
        "look_both": "Both Sides Elevation",
        "look_cut_only": "Cut Line Only",
        "mini_look_auto": "Auto (Left)",
        "mini_look_left": "Left Side",
        "mini_look_right": "Right Side",
        "mini_look_both": "Both Sides",
        "mini_look_cut_only": "Cut Only",
        "lbl_depth": "Depth:",
        "lbl_roads": "Roads:",
        "chk_sample_trees": "Sample Trees",
        "btn_refresh_profile": "Extract / Refresh Section",
        "btn_pick_ab_map": "Pick A - B Line on Map",

        "prof_status_waiting": "Ready — pick A and B points on map or click Refresh.",
        "prof_status_crit": (
            "CRITICAL SLOPE (>20%) | Max: {max_s:.1f}% (Avg: {avg_s:.1f}%) | "
            "Elev: +{min_z:.1f}m .. +{max_z:.1f}m (dZ {dz:.1f}m) | "
            "Length: {tot:.1f}m | Critical: {crit_l:.1f}m | Masses: {b_sum} | Look: {look} | Scale: {ex:.0f}x"
        ),
        "prof_status_ok": (
            "BALANCED TERRAIN | Max Slope: {max_s:.1f}% (Avg: {avg_s:.1f}%) | "
            "Elev: +{min_z:.1f}m .. +{max_z:.1f}m (dZ {dz:.1f}m) | "
            "Length: {tot:.1f}m | Masses: {b_sum} | Look: {look} | Scale: {ex:.0f}x"
        ),
        "mass_info_none": "Mass: None selected (click a building)",
        "mass_info_sel": "Mass #{idx}: {floors}F, {width:.1f} m",
        "lbl_floors": "Floors:",
        "lbl_width_m": "Width (m):",
        "btn_add_mass": "+ Add Mass",
        "btn_del_mass": "Delete Mass",
        "btn_add_trees": "+ Tree Cluster",
        "btn_prof_print": "Add to Print Layout",
        "btn_prof_svg": "Export Vector SVG",
        "btn_prof_png": "Export 300 DPI PNG",

        # Canvas / SVG text
        "canvas_right_of_way": "RIGHT-OF-WAY: {row:.2f} m ({status})",
        "canvas_balanced": "Balanced",
        "svg_row_width": "RIGHT-OF-WAY WIDTH: {row:.2f} m",
        "svg_subtitle": (
            "Pedestrian & Green: {ped_p}% ({ped_m:.2f}m)   |   "
            "Vehicle & Parking: {veh_p}% ({veh_m:.2f}m)   |   "
            "Cycling: {cyc_p}% ({cyc_m:.2f}m)   |   Scale: 1:100"
        ),
        "canvas_bus_sign": "B",
        "canvas_bus_led": "LINE 10 • CITY CENTER",
        "canvas_shop_left": "ARCHITECTURE STUDIO",
        "canvas_shop_right": "ARTISAN CAFE & BOOKS",
        "svg_car_plate": "URBAN-10",
        "svg_bus_led": "15 METRO EXPRESS",
        "svg_bus_plate": "TRANSIT 15",
        "svg_floor_suffix": "F",
        "pipe_gallery_short": "Utility Gallery",
        "pipe_gallery_tip": "Concrete Utility Gallery",
        "pipe_water_short": "Water 200",
        "pipe_water_tip": "Water Main (DN200)",
        "pipe_telecom_short": "Fiber",
        "pipe_telecom_tip": "Fiber / Telecom (DN110)",
        "pipe_power_short": "Power",
        "pipe_power_tip": "Power Conduit (DN125)",
        "pipe_sewer_short": "Sewer 600",
        "pipe_sewer_tip": "Sanitary Sewer (DN600)",
        "pipe_drainage_short": "Storm 400",
        "pipe_drainage_tip": "Storm Drain (DN400)",
        "pipe_gas_short": "Gas 100",
        "pipe_gas_tip": "Gas Main (DN100)",
        "pipe_click_remove": "Click to hide: {label}",

        # Profile Canvas & SVG
        "prof_crit_badge": "{pct:.0f}% Critical",
        "prof_slope_badge": "{pct:.0f}% Slope",
        "prof_empty_banner": "No buildings cut or inside corridor — adjust Look Direction or Depth",
        "prof_legend_cut": "Cut",
        "prof_legend_sil": "Elevation",
        "prof_sub_line": (
            "{src} | Look: {look} | Exag: {ex:.0f}x | Length: {len:.1f}m | "
            "Max Slope: {ms:.1f}% | Elev: {min_z:.1f}m - {max_z:.1f}m"
        ),
        "look_short_auto": "Auto",
        "look_short_left": "Left/N ({d:.0f}m)",
        "look_short_right": "Right/S ({d:.0f}m)",
        "look_short_both": "Both ({d:.0f}m)",
        "look_short_cut_only": "Cut Only",
        "look_name_auto": "Auto",
        "look_name_left": "Left",
        "look_name_right": "Right",
        "look_name_both": "Both",
        "look_name_cut_only": "Cut",
        "b_count_cut_sil": "{total} masses ({cut} cut, {sil} elev)",
        "b_count_simple": "{total} masses",

        # Model / GIS defaults
        "default_section_name": "Street Cross-Section",
        "default_profile_title": "1:1000 A-A' URBAN SECTION",
        "default_profile_bb_title": "1:1000 B-B' URBAN SECTION",
        "default_source_preset": "Sample Terrain Preset",
        "default_road_name": "Street",
        "default_bldg_label": "Building",
        "new_bldg_label": "New Mass",
        "urban_block_label": "Urban Block ({floors}F)",
        "preset_source_fallback": "Studio Sample Hill",
        "contours_source_fmt": "Contours ({name} - {field}, {cnt} hits)",
        "dem_source_fmt": "DEM ({name})",
        "dem_slope_source_fmt": "DEM ({dem}) + Slope ({slope})",

        # Dialogs & Alerts
        "msg_info": "Info",
        "msg_warn": "Warning",
        "msg_error": "Error",
        "msg_min_one_elem": "A section must contain at least 1 strip!",
        "msg_no_road_layer": "No valid line road layer found in the project.",
        "msg_no_sel_road": "No selected road feature found in '{name}'!",
        "msg_road_loaded": "Loaded template for {name} ({w:.1f} m)!",
        "msg_no_road_geom": "Please select a road line on the map first.",
        "msg_line_added": "Perpendicular A - A' section line added to 'Urban Section Lines' layer!",
        "msg_layout_added": "Cross-section inserted into QGIS Print Layout:\n{path}",
        "msg_saved": "Saved successfully:\n{path}",
        "msg_need_gui": "QGIS GUI environment is required for interactive map picking.",
        "msg_pick_bar": "A-B Section Tool: Click 1. Start (A) then 2. End (B) on the map.",
        "msg_prof_updated_title": "Section Updated",
        "msg_prof_updated": (
            "Topographic section refreshed!\n"
            "Source: {src}\nLength: {len:.1f} m\nElevation: {min_z:.1f}m - {max_z:.1f}m\n"
            "Buildings: {tot} masses (Cut: {cut}, Elevation: {sil})"
        ),
        "msg_prof_created_title": "Cross-Section Created",
        "msg_prof_created": (
            "Sampled {len:.1f} m A-B section line from map!\n"
            "Source: {src}\n"
            "Buildings: {tot} masses (Cut: {cut}, Elevation: {sil})\n"
            "Look Corridor: {look} ({depth:.0f} m)"
        ),
        "msg_multi_saved": "{n} 1:1000 SVG section sheets exported:\n{folder}",
        "file_dlg_dem": "Open DEM Elevation Raster",
        "file_dlg_slope": "Open Slope (%) Raster",
        "file_dlg_contour": "Open Contour Lines Layer",
        "file_dlg_svg": "Save Vector SVG",
        "file_dlg_png": "Save 300 DPI PNG",
        "file_dlg_folder": "Select Folder for Multi-Sheet SVGs",
    },
    "tr": {
        "window_title": "UrbanCrossSection — Kentsel Sokak ve 1/1000 A-B Kesit Stüdyosu",
        "brand_html": (
            "<b>UrbanCrossSection</b> "
            "<span style='color:#64748b;font-size:11px;'>| Sokak ve 1/1000 Topografik Kesit Motoru</span>"
        ),
        "mode_label": "Mod:",
        "mode_basic": "Temel",
        "mode_advanced": "Gelişmiş",
        "mode_tooltip": "Temel mod sade arayüz sunar; Gelişmiş mod tüm altyapı, GIS ve kütle araçlarını açar.",
        "lang_label": "Dil:",
        "btn_collapse": "Haritayı Gör",
        "btn_expand": "Paneli Büyüt",
        "mini_pick_init": "Haritada önce A, sonra B noktasına tıklayın...",
        "mini_pick_a": "Haritada 1. noktayı (A) tıklayın...",
        "mini_pick_b": "A belirlendi ({x:.1f}, {y:.1f}). B noktasını tıklayın...",
        "mini_calculating": "Kesit hesaplanıyor...",
        "mini_look": "Bakış:",
        "mini_expand": "Büyüt",
        "mini_cancel": "İptal",
        "tab_street": "Sokak Enkesiti",
        "tab_profile": "1/1000 Kentsel Silüet (A-B)",

        "lbl_template": "Şablon:",
        "lbl_road_name": "Yol Adı:",
        "lbl_corridor_width": "Genişlik (m):",
        "lbl_theme": "Tema:",
        "btn_read_map_road": "Haritadan Yolu Oku",
        "theme_architectural": "Mimari Jüri Renkli",
        "theme_technical_cad": "Teknik CAD (Monokrom)",
        "theme_sunset_warm": "Sıcak Stüdyo",
        "theme_night_lighting": "Gece Aydınlatma",
        "status_balanced": (
            "DENGELİ (1/100): Elemanlar {tot:.2f} m = Kırmızı Çizgi {row:.2f} m  |  "
            "Yaya/Yeşil: %{ped}  |  Taşıt/Park: %{veh}  |  Bisiklet: %{cyc}"
        ),
        "status_narrow": (
            "BOŞLUK VAR: Kırmızı Çizgi {row:.2f} m, Şeritler {tot:.2f} m "
            "(+{diff:.2f} m kaldı) — şerit ekleyin veya genişletin"
        ),
        "status_over": (
            "KIRMIZI ÇİZGİYİ AŞIYOR: Toplam ({tot:.2f} m) sınırı {over:.2f} m "
            "aşıyor — şeritleri daraltın"
        ),
        "lbl_selected_prefix": "Seçili:",
        "btn_move_left": "< Sola",
        "btn_move_right": "Sağa >",
        "btn_delete": "Sil",
        "chk_trees": "Ağaç",
        "chk_lighting": "Aydınlatma",
        "chk_bench": "Bank",
        "chk_bus_shelter": "Durak",
        "chk_tactile": "Engelli İzi",
        "chk_bike_rack": "Bisiklet Parkı",
        "lbl_vehicle": "Araç:",
        "veh_none": "Yok",
        "veh_car": "Otomobil",
        "veh_bus": "Otobüs",
        "lbl_people": "Yaya:",
        "lbl_add_strip": "Şerit Ekle:",
        "btn_utilities_show": "Altyapı & Katmanlar v",
        "btn_utilities_hide": "Altyapı & Katmanlar ^",
        "btn_buildings_show": "Yan Binalar v",
        "btn_buildings_hide": "Yan Binalar ^",

        "pal_sidewalk": "Kaldırım (2.0m)",
        "pal_landscape": "Yeşil Şerit (1.5m)",
        "pal_bike": "Bisiklet (1.5m)",
        "pal_vehicle": "Taşıt (3.25m)",
        "pal_bus": "Otobüs (3.5m)",
        "pal_parking": "Otopark (2.0m)",
        "pal_median": "Refüj (2.0m)",
        "pal_tram": "Tramvay (6.0m)",
        "pal_parklet": "Parklet (3.0m)",
        "pal_buffer": "Bordür (0.5m)",

        "lbl_utilities": "Altyapı:",
        "chk_util_water": "İçme Suyu (Ø200)",
        "chk_util_telecom": "Fiber (Ø110)",
        "chk_util_power": "Enerji (Ø125)",
        "chk_util_gas": "Doğalgaz (Ø100)",
        "chk_util_drainage": "Drenaj (Ø400)",
        "chk_util_sewer": "Atıksu (Ø600)",
        "chk_util_gallery": "Ortak Galeri",
        "tip_util_gallery": "İçme suyu, fiber ve enerji hatlarını betonarme kutu menfez galeri içinde toplar.",
        "btn_util_all": "Tümünü Aç",
        "btn_util_none": "Tümünü Kaldır",
        "lbl_visual_layers": "Katmanlar:",
        "chk_show_subgrade": "Zemin & Temel",
        "chk_show_buildings": "Yan Binalar",
        "chk_show_slopes": "%2 Enine Eğim",
        "chk_show_cards": "Üst Kartlar",
        "chk_show_dimensions": "Ölçü Zinciri",

        "lbl_left_floors": "Sol Kat:",
        "lbl_right_floors": "Sağ Kat:",
        "lbl_setback": "Ön Bahçe (m):",
        "lbl_sign": "Tabela:",

        "btn_map_line": "Haritada Kesit Çizgisi Ekle",
        "btn_print_layout": "Baskı Düzenine Ekle",
        "btn_export_svg": "SVG Kaydet",
        "btn_export_png": "PNG Kaydet (300 DPI)",
        "btn_close": "Kapat",

        "lbl_profile_preset": "Örnek Kesit:",
        "prof_preset_aa": "1/1000 A-A' Kentsel Tepe & Yamaç (700m)",
        "prof_preset_bb": "1/1000 B-B' Doğrusal Eğim & Vadi (450m)",
        "lbl_title": "Başlık:",
        "lbl_sky": "Gökyüzü:",
        "sky_sunset": "Gün Batımı",
        "sky_golden_hour": "Altın Saat",
        "sky_daylight": "Gündüz",
        "lbl_exag": "Düşey Abartı:",
        "exag_1": "1x (Doğal / 1:1)",
        "exag_2": "2x Abartı",
        "exag_3": "3x Abartı",
        "exag_5": "5x Abartı",
        "exag_10": "10x Abartı",
        "lbl_segment": "1/1000 Kesit Segmenti:",
        "btn_prev_seg": "< Önceki",
        "btn_next_seg": "Sonraki >",
        "btn_export_all_segs": "Tüm Paftaları Kaydet (SVG)",
        "seg_single": "Tek Bölüm ({len:.1f} m)",
        "seg_overview": "Tüm Hat Özeti ({len:.1f} m)",
        "seg_item": "Bölüm {idx}/{total} ({s}m - {e}m | {cnt} Kütle)",

        "box_topo_title": "Topografya, Yükseklik ve Bina Kaynağı",
        "lbl_source_mode": "Veri Modu:",
        "mode_dem": "DEM Yükseklik Rasterı",
        "mode_contours": "Eşyükselti (Vektör)",
        "mode_dem_slope": "DEM + Eğim Rasterı",
        "mode_preset": "Örnek Yamaç (Şablon)",
        "lbl_dem": "DEM:",
        "lbl_terrain_layer": "Arazi Katmanı:",
        "btn_load_dem": "DEM TIF...",
        "lbl_slope": "Eğim (%):",
        "btn_load_slope": "Eğim TIF...",
        "lbl_contour": "Eşyükselti:",
        "btn_load_contour": "Eşyükselti...",
        "lbl_elev_field": "Kot Alanı:",
        "lbl_bldg_layer": "Binalar:",
        "item_none_bldg": "Yok (Bina Katmanı Yok)",
        "item_none_slope": "Yok (DEM'den Hesapla)",
        "item_none_road": "Yok (Yol Katmanı Yok)",
        "lbl_floors_field": "Kat Alanı:",
        "lbl_step": "Adım:",
        "lbl_look": "Bakış Yönü:",
        "look_auto": "Otomatik (Sol / Karşı)",
        "look_left": "Sol Cephe (A->B Sol)",
        "look_right": "Sağ Cephe (A->B Sağ)",
        "look_both": "Her İki Taraf",
        "look_cut_only": "Sadece Kesilen",
        "mini_look_auto": "Oto (Sol)",
        "mini_look_left": "Sol Cephe",
        "mini_look_right": "Sağ Cephe",
        "mini_look_both": "Her İki Taraf",
        "mini_look_cut_only": "Sadece Kesilen",
        "lbl_depth": "Derinlik:",
        "lbl_roads": "Yollar:",
        "chk_sample_trees": "Temsilî Ağaçlar",
        "btn_refresh_profile": "Kesiti Çıkar / Yenile",
        "btn_pick_ab_map": "Haritada A - B Çiz",

        "prof_status_waiting": "Hazır — haritada A ve B noktalarını seçin veya Yenile'ye basın.",
        "prof_status_crit": (
            "KRİTİK EĞİM (>%20) | Maks: %{max_s:.1f} (Ort: %{avg_s:.1f}) | "
            "Kot: +{min_z:.1f}m .. +{max_z:.1f}m (Δ{dz:.1f}m) | "
            "Uzunluk: {tot:.1f}m | Kritik: {crit_l:.1f}m | Kütle: {b_sum} | Bakış: {look} | Abartı: {ex:.0f}x"
        ),
        "prof_status_ok": (
            "DENGELİ TOPOGRAFYA | Maks Eğim: %{max_s:.1f} (Ort: %{avg_s:.1f}) | "
            "Kot: +{min_z:.1f}m .. +{max_z:.1f}m (Δ{dz:.1f}m) | "
            "Uzunluk: {tot:.1f}m | Kütle: {b_sum} | Bakış: {look} | Abartı: {ex:.0f}x"
        ),
        "mass_info_none": "Kütle: Seçili yapı yok (bina üzerine tıklayın)",
        "mass_info_sel": "Kütle #{idx}: {floors} Kat, {width:.1f} m",
        "lbl_floors": "Kat:",
        "lbl_width_m": "Genişlik (m):",
        "btn_add_mass": "+ Kütle Ekle",
        "btn_del_mass": "Kütleyi Sil",
        "btn_add_trees": "+ Ağaç Kümesi",
        "btn_prof_print": "Baskı Paftasına Ekle",
        "btn_prof_svg": "Vektörel SVG Kaydet",
        "btn_prof_png": "300 DPI PNG Kaydet",

        "canvas_right_of_way": "KIRMIZI ÇİZGİ: {row:.2f} m ({status})",
        "canvas_balanced": "Dengeli",
        "svg_row_width": "KIRMIZI ÇİZGİ GENİŞLİĞİ: {row:.2f} m",
        "svg_subtitle": (
            "Yaya & Yeşil: %{ped_p} ({ped_m:.2f}m)   |   "
            "Taşıt & Park: %{veh_p} ({veh_m:.2f}m)   |   "
            "Bisiklet: %{cyc_p} ({cyc_m:.2f}m)   |   Ölçek: 1/100"
        ),
        "canvas_bus_sign": "D",
        "canvas_bus_led": "828 ESHOT • KONAK",
        "canvas_shop_left": "MİMARİ TASARIM STÜDYOSU",
        "canvas_shop_right": "ARTİSAN KAFE & KİTABEVİ",
        "svg_car_plate": "35 TR 1923",
        "svg_bus_led": "15 TİRE MERKEZ",
        "svg_bus_plate": "35 ESHOT 15",
        "svg_floor_suffix": " Kat",
        "pipe_gallery_short": "Altyapı Galerisi",
        "pipe_gallery_tip": "Ortak Altyapı Galerisi (Menfez)",
        "pipe_water_short": "Su Ø200",
        "pipe_water_tip": "İçme Suyu (Ø200 HDPE)",
        "pipe_telecom_short": "Fiber",
        "pipe_telecom_tip": "Fiber & Telekom (Ø110)",
        "pipe_power_short": "Enerji",
        "pipe_power_tip": "Enerji Kablosu (Ø125)",
        "pipe_sewer_short": "Atıksu Ø600",
        "pipe_sewer_tip": "Atıksu Kolektörü (Ø600)",
        "pipe_drainage_short": "Drenaj Ø400",
        "pipe_drainage_tip": "Yağmur Suyu Drenaj (Ø400)",
        "pipe_gas_short": "Gaz Ø100",
        "pipe_gas_tip": "Doğalgaz (Ø100 PE)",
        "pipe_click_remove": "Tıkla Kaldır: {label}",

        "prof_crit_badge": "%{pct:.0f} Eşik!",
        "prof_slope_badge": "%{pct:.0f} Eğim",
        "prof_empty_banner": "Hatta veya koridorda bina yok — Bakış Yönü / Derinlik artırabilirsiniz",
        "prof_legend_cut": "Kesilen",
        "prof_legend_sil": "Bakış Silüeti",
        "prof_sub_line": (
            "{src} | Bakış: {look} | Abartı: {ex:.0f}x | Uzunluk: {len:.1f}m | "
            "Maks Eğim: %{ms:.1f} | Kot: {min_z:.1f}m - {max_z:.1f}m"
        ),
        "look_short_auto": "Oto",
        "look_short_left": "Sol/Kuzey ({d:.0f}m)",
        "look_short_right": "Sağ/Güney ({d:.0f}m)",
        "look_short_both": "Çift Yön ({d:.0f}m)",
        "look_short_cut_only": "Sadece Kesit",
        "look_name_auto": "Oto",
        "look_name_left": "Sol",
        "look_name_right": "Sağ",
        "look_name_both": "Çift",
        "look_name_cut_only": "Kesilen",
        "b_count_cut_sil": "{total} bina ({cut} kesilen, {sil} silüet)",
        "b_count_simple": "{total} bina",

        "default_section_name": "Yol Kesiti",
        "default_profile_title": "1/1000 A-A' KESİT",
        "default_profile_bb_title": "1/1000 B-B' KESİT",
        "default_source_preset": "Varsayılan Şablon",
        "default_road_name": "İmar Yolu",
        "default_bldg_label": "Konut",
        "new_bldg_label": "Yeni Yapı",
        "urban_block_label": "Kentsel Blok ({floors}K)",
        "preset_source_fallback": "Varsayılan Stüdyo Tepesi",
        "contours_source_fmt": "Eşyükselti ({name} - {field}, {cnt} kesişim)",
        "dem_source_fmt": "DEM ({name})",
        "dem_slope_source_fmt": "DEM ({dem}) + Eğim ({slope})",

        "msg_info": "Bilgi",
        "msg_warn": "Uyarı",
        "msg_error": "Hata",
        "msg_min_one_elem": "Kesitte en az 1 eleman bulunmalıdır!",
        "msg_no_road_layer": "Haritada geçerli çizgi yol katmanı bulunamadı.",
        "msg_no_sel_road": "'{name}' katmanında seçili yol objesi bulunamadı!",
        "msg_road_loaded": "{name} ({w:.1f} m) şablonu yüklendi!",
        "msg_no_road_geom": "Lütfen önce haritada bir yol çizgisi seçin.",
        "msg_line_added": "'Kentsel Kesit Hatları' katmanına A - A' kesit çizgisi eklendi!",
        "msg_layout_added": "Kesit QGIS Baskı Düzenine eklendi:\n{path}",
        "msg_saved": "Başarıyla kaydedildi:\n{path}",
        "msg_need_gui": "Harita çizim aracı için QGIS GUI ortamı gereklidir.",
        "msg_pick_bar": "A-B Kesit Çizimi: Haritada 1. Başlangıç (A) ve 2. Bitiş (B) noktalarına tıklayın.",
        "msg_prof_updated_title": "Kesit Güncellendi",
        "msg_prof_updated": (
            "Topografya profili yenilendi!\n"
            "Kaynak: {src}\nUzunluk: {len:.1f} m\nKot Aralığı: {min_z:.1f}m - {max_z:.1f}m\n"
            "Binalar: {tot} kütle (Kesilen: {cut}, Silüet: {sil})"
        ),
        "msg_prof_created_title": "Kesit Oluşturuldu",
        "msg_prof_created": (
            "Haritadan {len:.1f} m A-B kesit hattı okundu!\n"
            "Kaynak: {src}\n"
            "Yapılar: {tot} kütle (Kesilen: {cut}, Silüet: {sil})\n"
            "Bakış Koridoru: {look} ({depth:.0f} m)"
        ),
        "msg_multi_saved": "{n} adet 1/1000 SVG pafta kaydedildi:\n{folder}",
        "file_dlg_dem": "DEM Yükseklik Rasterı Aç",
        "file_dlg_slope": "Eğim (%) Rasterı Aç",
        "file_dlg_contour": "Eşyükselti Katmanı Aç",
        "file_dlg_svg": "Vektörel SVG Kaydet",
        "file_dlg_png": "300 DPI PNG Kaydet",
        "file_dlg_folder": "Tüm Bölümler İçin Klasör Seç",
    },
}


def tr_text(key: str, lang: Optional[str] = None, **kwargs) -> str:
    """Translate string key to target language ('en' or 'tr') and format kwargs."""
    use_lang = normalize_lang(lang or _ACTIVE_LANG)
    table = STRINGS.get(use_lang, STRINGS["en"])
    raw = table.get(key, STRINGS["en"].get(key, key))
    if kwargs:
        try:
            return raw.format(**kwargs)
        except Exception:
            return raw
    return raw


ELEMENT_LABELS = {
    "en": {
        "sidewalk": "Sidewalk",
        "landscape": "Green Verge",
        "bike_lane": "Bike Lane",
        "parking": "Parking Lane",
        "vehicle_lane": "Travel Lane",
        "bus_lane": "Bus Lane",
        "median": "Median",
        "tram_lane": "Tramway",
        "buffer": "Curb Buffer",
        "parklet": "Cafe Parklet",
    },
    "tr": {
        "sidewalk": "Yaya Kaldırımı",
        "landscape": "Ağaçlandırma Bandı",
        "bike_lane": "Bisiklet Yolu",
        "parking": "Otopark Şeridi",
        "vehicle_lane": "Taşıt Şeridi",
        "bus_lane": "Otobüs Şeridi",
        "median": "Orta Refüj",
        "tram_lane": "Tramvay Hattı",
        "buffer": "Güvenlik Bandı",
        "parklet": "Kafe / Cep Parklet",
    },
}

# Known preset lane labels mapped bilaterally so switching EN <-> TR translates presets cleanly
LABEL_PAIRS = [
    ("Sidewalk (Left)", "Yaya Kaldırımı (Sol)"),
    ("Sidewalk (Right)", "Yaya Kaldırımı (Sağ)"),
    ("Wide Sidewalk (Right)", "Geniş Yaya Kaldırımı (Sağ)"),
    ("Promenade Sidewalk (Left)", "Yaya Gezinti Yolu (Sol)"),
    ("Tree-Lined Sidewalk (Right)", "Ağaçlı Kaldırım (Sağ)"),
    ("Frontage Sidewalk (Left)", "Yan Yol Kaldırımı (Sol)"),
    ("Frontage Sidewalk (Right)", "Yan Yol Kaldırımı (Sağ)"),
    ("Shared Travel Way (30 km/h)", "Paylaşımlı Taşıt Yolu (30 km/h)"),
    ("Travel Lane (Inbound)", "Taşıt Şeridi (Gidiş)"),
    ("Travel Lane (Outbound)", "Taşıt Şeridi (Geliş)"),
    ("Travel Lane 1 (Inbound)", "Taşıt Şeridi 1 (Gidiş)"),
    ("Travel Lane 2 (Inbound)", "Taşıt Şeridi 2 (Gidiş)"),
    ("Travel Lane 1 (Outbound)", "Taşıt Şeridi 1 (Geliş)"),
    ("Travel Lane 2 (Outbound)", "Taşıt Şeridi 2 (Geliş)"),
    ("Mainline 3 Lanes (Inbound)", "Ana Gövde 3 Şerit (Gidiş)"),
    ("Mainline 3 Lanes (Outbound)", "Ana Gövde 3 Şerit (Geliş)"),
    ("Frontage 2 Lanes (Left)", "Yan Yol 2 Şerit (Sol)"),
    ("Frontage 2 Lanes (Right)", "Yan Yol 2 Şerit (Sağ)"),
    ("One-Way Bike Lane", "Tek Yön Bisiklet Yolu"),
    ("Protected Bike Lane", "Ayrılmış Bisiklet Yolu"),
    ("Two-Way Cycle Track", "Çift Yön Bisiklet Yolu"),
    ("Parallel Parking Lane", "Paralel Otopark Şeridi"),
    ("Parallel Parking", "Paralel Park Şeridi"),
    ("Green Verge", "Ağaçlandırma Bandı"),
    ("Green Median", "Yeşil Orta Refüj"),
    ("Planted Median", "Ağaçlı Orta Refüj"),
    ("Wide Median / Barrier", "Geniş Orta Refüj / Bariyer"),
    ("Green Buffer (Left)", "Ayırıcı Yeşil Şerit (Sol)"),
    ("Green Buffer (Right)", "Ayırıcı Yeşil Şerit (Sağ)"),
    ("Safety Buffer", "Güvenlik Bordürü"),
    ("Dual Grassy Tramway", "Çift Hat Çimli Tramvay Hattı"),
    ("Grassy Tramway", "Çimli Tramvay"),
    ("Cafe Parklet", "Kafe Parklet"),
    ("Cafe Terrace (Left)", "Dükkan Önü Teras & Masalar (Sol)"),
    ("Cafe Terrace (Right)", "Dükkan Önü Kafe Terası (Sağ)"),
    ("Pedestrian Mall & Emergency Spine", "Ana Yaya Gezinti & Acil Koridor"),
    ("Sidewalk", "Yaya Kaldırımı"),
    ("Bike Lane", "Bisiklet Yolu"),
    ("Travel Lane", "Taşıt Şeridi"),
    ("Bus Lane", "Otobüs Şeridi"),
    ("Curb Buffer", "Güvenlik Bandı"),
]

SHOP_PAIRS = [
    ("CAFE & BOOKS", "KAFE & KİTABEVİ"),
    ("PHARMACY & BAKERY", "ECZANE & PASTANE"),
    ("BAKERY & MARKET", "BAKKAL & FIRIN"),
    ("CAFE & BISTRO", "KAFE & BİSTRO"),
    ("CAFE & BAKERY", "PASTANE & FIRIN"),
    ("BOOKSHOP & CAFE", "KİTABEVİ & KAFE"),
    ("PHARMACY", "ECZANE"),
    ("BANK & OFFICES", "BANKA & OFİS"),
    ("BISTRO & TERRACE", "RESTORAN & TERAS"),
    ("FASHION & BOUTIQUE", "MODA & BUTİK"),
    ("HOTEL & CAFE", "BÜYÜK OTEL & KAFE"),
    ("BUSINESS CENTER", "İŞ MERKEZİ & KAFELER"),
    ("CULTURAL CENTER", "KÜLTÜR MERKEZİ"),
    ("ART GALLERY", "SANAT GALERİSİ"),
    ("BISTRO CAFE", "BİSTRO KAFE"),
]

PRESET_SECTION_PAIRS = [
    ("7 m Calmed Residential Street", "7 m Sakinleştirilmiş Konut Sokağı"),
    ("10 m Neighborhood Collector", "10 m Mahalle İçi Dağıtıcı Sokak"),
    ("12 m Urban Bike Street", "12 m Kentsel Dağıtıcı Sokak"),
    ("12 m Pedestrian Retail Mall", "12 m Yayalaştırılmış Ticaret Sokağı"),
    ("15 m District Collector Avenue", "15 m Bölge Toplayıcı Cadde"),
    ("20 m Divided Arterial Boulevard", "20 m Ana Arter / Bulvar"),
    ("25 m Multi-Modal Boulevard", "25 m Bölünmüş Prestij Bulvarı"),
    ("30 m Transit Tramway Boulevard", "30 m Tramvaylı Prestij Bulvarı"),
    ("50 m Express Highway Corridor", "50 m Ekspres Çevre Yolu"),
    ("15 m District Collector Road", "15 m Bölge Dağıtıcı Yol"),
    ("Street Cross-Section", "Yol Kesiti"),
]

PRESET_INFO = {
    "7m": {
        "en": ("7 m Calmed Residential Street", "Shared local street with 30 km/h speed zone and side greenery."),
        "tr": ("7 m Sakinleştirilmiş Konut Sokağı", "Yaya öncelikli, 30 km/s hız limitli konut imar yolu."),
    },
    "10m": {
        "en": ("10 m Neighborhood Collector", "Two-way local neighborhood distributor with 2m sidewalks."),
        "tr": ("10 m Mahalle İçi Dağıtıcı Sokak", "Standart mahalle içi iki yönlü dağıtıcı yol."),
    },
    "12m": {
        "en": ("12 m Urban Bike Street", "Neighborhood avenue with dedicated 1.5m protected bike lane."),
        "tr": ("12 m Kentsel Dağıtıcı Sokak", "Bisiklet yolu entegreli 12m dağıtıcı yol standardı."),
    },
    "12m_pedestrian": {
        "en": ("12 m Pedestrian Retail Mall", "Car-free shared plaza with outdoor cafe parklets and trees."),
        "tr": ("12 m Yayalaştırılmış Ticaret Sokağı", "Taşıtsız, kafelerin ve ağaçların yer aldığı canlı ticaret sokağı."),
    },
    "15m": {
        "en": ("15 m District Collector Avenue", "Balanced collector with bike track, parallel parking, and wide sidewalks."),
        "tr": ("15 m Bölge Toplayıcı Cadde", "Paralel park, bisiklet yolu, ağaçlı kaldırımlar ve otobüs durağı."),
    },
    "20m": {
        "en": ("20 m Divided Arterial Boulevard", "2x2 divided arterial with planted median and bike lane."),
        "tr": ("20 m Ana Arter / Bulvar", "2x2 bölünmüş yol, ağaçlı orta refüj ve bisiklet yolu içeren ana arter."),
    },
    "25m": {
        "en": ("25 m Multi-Modal Boulevard", "Prestige boulevard with two-way cycle track, trees and transit lanes."),
        "tr": ("25 m Bölünmüş Prestij Bulvarı", "Çift yön bisiklet yollu ve ağaçlı refüjlü 25m bulvar."),
    },
    "30m": {
        "en": ("30 m Transit Tramway Boulevard", "30m multi-modal corridor featuring a central grassy tramway."),
        "tr": ("30 m Tramvaylı Prestij Bulvarı", "Ortasından çimli tramvay hattı geçen 30m metropol bulvarı."),
    },
    "50m": {
        "en": ("50 m Express Highway Corridor", "Express corridor with 3x3 mainline, green buffers and frontage roads."),
        "tr": ("50 m Ekspres Çevre Yolu", "Yan yollu, 3x3 ana gövdeli 50m çevre yolu enkesiti."),
    },
}


def element_default_label(elem_type: str, lang: Optional[str] = None) -> str:
    use_lang = normalize_lang(lang or _ACTIVE_LANG)
    return ELEMENT_LABELS.get(use_lang, ELEMENT_LABELS["en"]).get(
        elem_type, "Strip" if use_lang == "en" else "Yol Elemanı"
    )


def translate_known_pair(text: str, pairs, target_lang: str) -> str:
    if not text:
        return text
    tgt = normalize_lang(target_lang)
    idx_src = 1 if tgt == "en" else 0
    idx_dst = 0 if tgt == "en" else 1
    for a, b in pairs:
        pair = (a, b)
        if text == pair[idx_src]:
            return pair[idx_dst]
    return text


def retranslate_section_inplace(sec, target_lang: str):
    """Update translatable built-in display strings on CrossSection without altering geometry."""
    if not sec:
        return
    tgt = normalize_lang(target_lang)
    if hasattr(sec, "language"):
        sec.language = tgt
    sec.name = translate_known_pair(sec.name, PRESET_SECTION_PAIRS, tgt)
    for elem in getattr(sec, "elements", []):
        elem.label = translate_known_pair(elem.label, LABEL_PAIRS, tgt)
    if getattr(sec, "left_building", None):
        sec.left_building.shop_name = translate_known_pair(sec.left_building.shop_name, SHOP_PAIRS, tgt)
    if getattr(sec, "right_building", None):
        sec.right_building.shop_name = translate_known_pair(sec.right_building.shop_name, SHOP_PAIRS, tgt)


def retranslate_profile_inplace(prof, target_lang: str):
    """Update translatable built-in display strings on UrbanProfile without altering terrain/masses."""
    if not prof:
        return
    tgt = normalize_lang(target_lang)
    if hasattr(prof, "language"):
        prof.language = tgt
    title_pairs = [
        ("1:1000 A-A' URBAN SECTION", "1/1000 A-A' KESİT"),
        ("1:1000 B-B' URBAN SECTION", "1/1000 B-B' KESİT"),
    ]
    prof.title = translate_known_pair(prof.title, title_pairs, tgt)
    src_pairs = [
        ("Sample Terrain Preset", "Varsayılan Şablon"),
        ("Studio Sample Hill", "Varsayılan Stüdyo Tepesi"),
    ]
    prof.source_layer_name = translate_known_pair(prof.source_layer_name, src_pairs, tgt)
    bldg_pairs = [
        ("Residential", "Konut"),
        ("Summit Facility", "Zirve Tesis"),
        ("Mixed Use", "Karma Kullanım"),
        ("Commercial Hub", "Ticaret Merkezi"),
        ("Commercial", "Ticaret"),
        ("Housing Block", "Toplu Konut"),
        ("Building", "Yapı"),
        ("New Mass", "Yeni Yapı"),
    ]
    for b in getattr(prof, "buildings", []):
        b.label = translate_known_pair(b.label, bldg_pairs, tgt)
    road_pairs = [
        ("12 m Planned Street", "12 m İmar Yolu"),
        ("15 m Collector Avenue", "15 m Toplayıcı Cadde"),
        ("10 m Local Street", "10 m Sokak"),
        ("15 m District Road", "15 m Bölge Yolu"),
        ("Planned Street", "İmar Yolu"),
        ("Street", "İmar Yolu"),
    ]
    for r in getattr(prof, "roads", []):
        r.name = translate_known_pair(r.name, road_pairs, tgt)
