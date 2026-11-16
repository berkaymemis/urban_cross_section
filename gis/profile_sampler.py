# -*- coding: utf-8 -*-
"""UrbanCrossSection — Haritadan A-B Kesiti Örnekleme ve Topografya Entegrasyonu (gis/profile_sampler.py).

Qt5 (QGIS 3) ve Qt6 (QGIS 4) tam uyumlu.
Harita üzerindeki A ve B noktaları arasından geçen doğru boyunca:
1. DEM / Sayısal Yükseklik Modeli (Raster) yüksek hassasiyetli örnekleme (CRS dönüşümü dahil).
2. Eğim Rasterı (% eğim) doğrudan sorgulama veya sayısal gradyan hesabı.
3. Eşyükselti Eğrileri (Vektör İzoipsler) geometrik kesişim ve PCHIP monoton kübik enterpolasyon.
4. Bina poligonları (kat adedi ve taban kotu) ve yol kesişimlerinin kentsel profile aktarılması.
"""

import math
import re
from typing import Optional, List, Tuple, Dict, Any

from qgis.core import (
    QgsProject,
    QgsPointXY,
    QgsGeometry,
    QgsRasterLayer,
    QgsVectorLayer,
    QgsWkbTypes,
    QgsFeatureRequest,
    QgsCoordinateTransform,
    QgsCoordinateReferenceSystem,
)

from ..core.profile_model import (
    UrbanProfile,
    BuildingMass,
    VegetationCluster,
    RoadIncision,
    pchip_interpolate_series,
)
from ..core.i18n import get_language, normalize_lang, tr_text


def find_dem_raster_layer() -> Optional[QgsRasterLayer]:
    """Projedeki Sayısal Yükseklik Modeli (DEM / DTM / SRTM) raster katmanını bulur."""
    proj = QgsProject.instance()
    for layer in proj.mapLayers().values():
        if isinstance(layer, QgsRasterLayer) and layer.isValid():
            name_lower = layer.name().lower()
            if any(k in name_lower for k in ("dem", "dtm", "srtm", "yukseklik", "elevation", "topografya")):
                # Eğim rasterı olmamalı
                if "egim" not in name_lower and "slope" not in name_lower:
                    return layer
    # Herhangi bir raster katman varsa ilkini döndür
    for layer in proj.mapLayers().values():
        if isinstance(layer, QgsRasterLayer) and layer.isValid():
            name_lower = layer.name().lower()
            if "egim" not in name_lower and "slope" not in name_lower:
                return layer
    return None


def find_slope_raster_layer() -> Optional[QgsRasterLayer]:
    """Projedeki Eğim (%) raster katmanını bulur."""
    proj = QgsProject.instance()
    for layer in proj.mapLayers().values():
        if isinstance(layer, QgsRasterLayer) and layer.isValid():
            name_lower = layer.name().lower()
            if any(k in name_lower for k in ("egim", "slope", "meyil", "yuzde")):
                return layer
    return None


def find_contour_vector_layer() -> Optional[QgsVectorLayer]:
    """Projedeki eşyükselti eğrileri (münhani / izoips / contour) vektör çizgi katmanını bulur."""
    proj = QgsProject.instance()
    for layer in proj.mapLayers().values():
        if isinstance(layer, QgsVectorLayer) and layer.isValid():
            if layer.geometryType() == QgsWkbTypes.LineGeometry:
                name_lower = layer.name().lower()
                if any(k in name_lower for k in ("esyukselti", "es_yukselti", "contour", "izoips", "munhani", "kot", "egri")):
                    return layer
    return None


def detect_elevation_field(layer: QgsVectorLayer) -> Optional[str]:
    """Eşyükselti katmanında kot / yükseklik öznitelik alanını tespit eder."""
    if not layer or not layer.isValid():
        return None
    field_names = [f.name() for f in layer.fields()]
    for candidate in ("kot", "elevation", "elev", "yukseklik", "z", "level", "height", "rakim", "kontur"):
        for fn in field_names:
            if candidate == fn.lower():
                return fn
    # İkincil arama (içeren)
    for fn in field_names:
        fn_l = fn.lower()
        if any(c in fn_l for c in ("kot", "elev", "yuksek", "rakim")):
            return fn
    return field_names[0] if field_names else None


def find_building_polygon_layer() -> Optional[QgsVectorLayer]:
    """Projedeki bina veya yapı poligon katmanını bulur."""
    proj = QgsProject.instance()
    for layer in proj.mapLayers().values():
        if isinstance(layer, QgsVectorLayer) and layer.isValid():
            if layer.geometryType() == QgsWkbTypes.PolygonGeometry:
                name_lower = layer.name().lower()
                if any(k in name_lower for k in ("bina", "yapi", "building", "structure", "konut", "mevcut_durum", "ada")):
                    return layer
    return None


def detect_building_floors_field(layer: QgsVectorLayer) -> Optional[str]:
    """Bina katmanında kat adedi alanını tespit eder (MAKS/TAKBİS/yerel adlar dahil)."""
    if not layer or not layer.isValid():
        return None
    field_names = [f.name() for f in layer.fields()]
    exact_cands = (
        "zeminustukatsayisi",
        "kat_sayisi",
        "katsayisi",
        "ortalama_kat",
        "kat",
        "kat_adedi",
        "katadedi",
        "bina_kat",
        "max_kat",
        "floors",
        "num_floors",
        "height",
        "yukseklik",
        "h",
    )
    for candidate in exact_cands:
        for fn in field_names:
            if candidate == fn.lower():
                return fn
    for fn in field_names:
        fn_l = fn.lower()
        if any(tok in fn_l for tok in ("kat", "floor")):
            return fn
    return None


def parse_floor_count(raw_val: Any) -> Optional[int]:
    """Türkçe öznitelik değerlerinden ('4', '4.0', '3,5', '4 Kat', 'Z+3', 'B+Z+4') net kat sayısını çözer."""
    if raw_val is None:
        return None
    if isinstance(raw_val, (int, float)):
        if math.isnan(float(raw_val)) or float(raw_val) <= 0:
            return None
        return max(1, int(round(float(raw_val))))

    s = str(raw_val).strip().upper()
    if not s or s in ("NULL", "NONE", "YOK", "-", "0"):
        return None

    # 'Z+3' veya 'B+Z+4' biçimleri (Z = Zemin + üst katlar; bodrumu zemin üstüne katmayalım veya 1+N alalım)
    m_z = re.search(r"Z\s*\+\s*(\d+)", s)
    if m_z:
        return max(1, 1 + int(m_z.group(1)))

    # Genel sayısal ifade ('4 Kat', '3,5', '5K')
    s_num = s.replace(",", ".")
    m_n = re.search(r"(\d+(?:\.\d+)?)", s_num)
    if m_n:
        val_f = float(m_n.group(1))
        if val_f > 0:
            return max(1, int(round(val_f)))
    return None


def find_road_layer() -> Optional[QgsVectorLayer]:
    """Projedeki yol / cadde / imar hattı çizgi veya poligon katmanını bulur."""
    proj = QgsProject.instance()
    for layer in proj.mapLayers().values():
        if isinstance(layer, QgsVectorLayer) and layer.isValid():
            name_lower = layer.name().lower()
            if any(k in name_lower for k in ("yol", "road", "cadde", "sokak", "arter", "street", "ulasim")):
                return layer
    return None


# -----------------------------------------------------------------------------
# 1. DEM RASTER ÖRNEKLEME MOTORU (Yüksek Hassasiyet + CRS Dönüşümü)
# -----------------------------------------------------------------------------

def sample_profile_from_dem(
    pt_a: QgsPointXY,
    pt_b: QgsPointXY,
    dem_layer: QgsRasterLayer,
    slope_layer: Optional[QgsRasterLayer] = None,
    step_meters: float = 2.0,
    project_crs: Optional[QgsCoordinateReferenceSystem] = None,
) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]]]:
    """Sayısal Yükseklik Modeli (DEM) rasterından A-B kesiti boyunca kot ve eğim örnekler."""
    dx = pt_b.x() - pt_a.x()
    dy = pt_b.y() - pt_a.y()
    total_len = math.hypot(dx, dy)
    if total_len < 1.0:
        total_len = 100.0

    num_samples = max(2, int(math.ceil(total_len / max(0.5, step_meters))) + 1)
    actual_step = total_len / float(num_samples - 1)

    proj = QgsProject.instance()
    p_crs = project_crs or proj.crs()
    dem_crs = dem_layer.crs()

    # DEM Koordinat Dönüştürücü
    need_dem_transform = (p_crs.isValid() and dem_crs.isValid() and p_crs != dem_crs)
    xform_dem = QgsCoordinateTransform(p_crs, dem_crs, proj) if need_dem_transform else None

    # Eğim Rasterı Koordinat Dönüştürücü
    xform_slope = None
    if slope_layer and slope_layer.isValid():
        sl_crs = slope_layer.crs()
        if p_crs.isValid() and sl_crs.isValid() and p_crs != sl_crs:
            xform_slope = QgsCoordinateTransform(p_crs, sl_crs, proj)

    dem_provider = dem_layer.dataProvider()
    slope_provider = slope_layer.dataProvider() if (slope_layer and slope_layer.isValid()) else None

    terrain_pts: List[Tuple[float, float]] = []
    slope_pts: List[Tuple[float, float]] = []

    last_valid_elev = None

    for i in range(num_samples):
        cur_dist = i * actual_step
        t = cur_dist / total_len
        map_x = pt_a.x() + t * dx
        map_y = pt_a.y() + t * dy
        map_pt = QgsPointXY(map_x, map_y)

        # 1. DEM Sorgusu: QGIS C++ SIP bindings return tuple (value: float, ok: bool)
        dem_pt = xform_dem.transform(map_pt) if xform_dem else map_pt
        ident = dem_provider.sample(dem_pt, 1)

        elev = None
        if ident is not None:
            # SIP tuple (val, ok)
            val, ok = ident if isinstance(ident, (tuple, list)) else (ident, True)
            if ok and not math.isnan(val) and val > -9000.0:
                elev = float(val)
                last_valid_elev = float(val)

        if elev is None:
            elev = last_valid_elev if last_valid_elev is not None else 100.0

        terrain_pts.append((round(cur_dist, 2), round(elev, 2)))

        # 2. Eğim Rasterı Sorgusu (Varsa)
        if slope_provider:
            sl_pt = xform_slope.transform(map_pt) if xform_slope else map_pt
            s_ident = slope_provider.sample(sl_pt, 1)
            slp_val = 0.0
            if s_ident is not None:
                s_val, s_ok = s_ident if isinstance(s_ident, (tuple, list)) else (s_ident, True)
                if s_ok and not math.isnan(s_val) and 0.0 <= s_val < 500.0:
                    slp_val = float(s_val)
            slope_pts.append((round(cur_dist, 2), round(slp_val, 2)))

    # Eğer eğim rasterı yoksa sayısal gradyandan hesapla
    if not slope_pts and len(terrain_pts) >= 2:
        n = len(terrain_pts)
        for i in range(n):
            dist_i, z_i = terrain_pts[i]
            if i == 0:
                d_next, z_next = terrain_pts[1]
                ds = max(0.1, d_next - dist_i)
                slp = abs(z_next - z_i) / ds * 100.0
            elif i == n - 1:
                d_prev, z_prev = terrain_pts[n - 2]
                ds = max(0.1, dist_i - d_prev)
                slp = abs(z_i - z_prev) / ds * 100.0
            else:
                d_prev, z_prev = terrain_pts[i - 1]
                d_next, z_next = terrain_pts[i + 1]
                ds = max(0.2, d_next - d_prev)
                slp = abs(z_next - z_prev) / ds * 100.0
            slope_pts.append((dist_i, round(slp, 2)))

    return terrain_pts, slope_pts


# -----------------------------------------------------------------------------
# 2. EŞYÜKSELTİ EĞRİLERİ (VEKTÖR İZOİPS) ÖRNEKLEME MOTORU (PCHIP ENTERPOLASYON)
# -----------------------------------------------------------------------------

def sample_profile_from_contours(
    pt_a: QgsPointXY,
    pt_b: QgsPointXY,
    contour_layer: QgsVectorLayer,
    elev_field: str = "kot",
    step_meters: float = 2.0,
    project_crs: Optional[QgsCoordinateReferenceSystem] = None,
    out_crossings: Optional[List[Tuple[float, float]]] = None,
) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]]]:
    """Eşyükselti eğrileri vektör katmanını kesiştirerek PCHIP ile pürüzsüz profil üretir."""
    dx = pt_b.x() - pt_a.x()
    dy = pt_b.y() - pt_a.y()
    total_len = math.hypot(dx, dy)
    if total_len < 1.0:
        total_len = 100.0
        ux, uy = 1.0, 0.0
    else:
        ux, uy = dx / total_len, dy / total_len

    proj = QgsProject.instance()
    p_crs = project_crs or proj.crs()
    vec_crs = contour_layer.crs()

    need_transform = (p_crs.isValid() and vec_crs.isValid() and p_crs != vec_crs)
    xform_to_vec = QgsCoordinateTransform(p_crs, vec_crs, proj) if need_transform else None
    xform_back = QgsCoordinateTransform(vec_crs, p_crs, proj) if need_transform else None

    # Kesit hattı geometrisi
    section_line = QgsGeometry.fromPolylineXY([pt_a, pt_b])
    if xform_to_vec:
        section_line_vec = QgsGeometry(section_line)
        section_line_vec.transform(xform_to_vec)
    else:
        section_line_vec = section_line

    # Kesişen eşyükselti eğrilerini topla
    intersections: List[Tuple[float, float]] = []

    req = QgsFeatureRequest().setFilterRect(section_line_vec.boundingBox())
    for feat in contour_layer.getFeatures(req):
        geom = feat.geometry()
        if not geom or geom.isEmpty():
            continue
        if geom.intersects(section_line_vec):
            inter = geom.intersection(section_line_vec)
            if inter.isEmpty():
                continue

            # Kot değerini oku (Güvenli kontrol)
            elev_val = None
            if elev_field and elev_field in feat.fields().names():
                raw_val = feat[elev_field]
                if raw_val not in (None, ""):
                    try:
                        elev_val = float(str(raw_val).replace(",", "."))
                    except (ValueError, TypeError):
                        pass

            if elev_val is None:
                continue

            # Point, MultiPoint, LineString veya GeometryCollection tüm düğümlerini güvenli topla
            pts = [QgsPointXY(v) for v in inter.vertices()]
            for p in pts:
                map_p = xform_back.transform(p) if xform_back else p
                # Kesit doğrusu üzerine ortogonal izdüşüm mesafesi
                dist_m = (map_p.x() - pt_a.x()) * ux + (map_p.y() - pt_a.y()) * uy
                if -0.5 <= dist_m <= total_len + 0.5:
                    dist_m = max(0.0, min(total_len, dist_m))
                    intersections.append((round(dist_m, 2), elev_val))

    # Kesişimleri mesafeye göre sırala ve aynı noktadaki mükerrerleri tekilleştir
    intersections.sort(key=lambda item: item[0])
    if intersections:
        deduped = [intersections[0]]
        for d_m, z_v in intersections[1:]:
            if abs(d_m - deduped[-1][0]) > 0.2:
                deduped.append((d_m, z_v))
        intersections = deduped

    if out_crossings is not None:
        out_crossings.clear()
        out_crossings.extend(intersections)

    # Eğer hiç kesişim bulunamadıysa (hat iki eşyükselti eğrisi arasında kalmışsa): yakın kutuda ara
    if not intersections:
        fallback_elev = 100.0
        search_box = section_line_vec.boundingBox()
        search_box.grow(max(50.0, total_len * 0.5))
        best_dist = float("inf")
        for f in contour_layer.getFeatures(QgsFeatureRequest().setFilterRect(search_box)):
            fg = f.geometry()
            if not fg or fg.isEmpty():
                continue
            d_near = fg.distance(section_line_vec)
            if d_near < best_dist and elev_field in f.fields().names():
                try:
                    ev = float(str(f[elev_field]).replace(",", "."))
                    best_dist = d_near
                    fallback_elev = ev
                except Exception:
                    pass
        intersections = [(0.0, fallback_elev), (total_len, fallback_elev)]

    # Uç noktaları tamamla (Başlangıç ve Bitiş)
    if intersections[0][0] > 0.1:
        intersections.insert(0, (0.0, intersections[0][1]))
    if intersections[-1][0] < total_len - 0.1:
        intersections.append((total_len, intersections[-1][1]))

    # İstenen düzenli aralıklarla PCHIP enterpolasyonu yap
    num_eval = max(2, int(math.ceil(total_len / max(0.5, step_meters))) + 1)
    eval_step = total_len / float(num_eval - 1)
    eval_x = [i * eval_step for i in range(num_eval)]

    terrain_pts = pchip_interpolate_series(intersections, eval_x)

    # Eğim serisi hesapla
    slope_pts = []
    n = len(terrain_pts)
    for i in range(n):
        dist_i, z_i = terrain_pts[i]
        if i == 0:
            d_next, z_next = terrain_pts[1]
            ds = max(0.1, d_next - dist_i)
            slp = abs(z_next - z_i) / ds * 100.0
        elif i == n - 1:
            d_prev, z_prev = terrain_pts[n - 2]
            ds = max(0.1, dist_i - d_prev)
            slp = abs(z_i - z_prev) / ds * 100.0
        else:
            d_prev, z_prev = terrain_pts[i - 1]
            d_next, z_next = terrain_pts[i + 1]
            ds = max(0.2, d_next - d_prev)
            slp = abs(z_next - z_prev) / ds * 100.0
        slope_pts.append((dist_i, round(slp, 2)))

    return terrain_pts, slope_pts


# -----------------------------------------------------------------------------
# 3. MASTER KOMBİNE PROFİL ÖRNEKLEYİCİ
# -----------------------------------------------------------------------------

def _extract_feature_floors(feat, primary_field: Optional[str]) -> int:
    """Bina katmanından güvenilir şekilde kat adedi çeker."""
    fnames = feat.fields().names()
    if primary_field and primary_field in fnames:
        parsed = parse_floor_count(feat[primary_field])
        if parsed is not None:
            return parsed

    for fn_cand in (
        "zeminustukatsayisi",
        "kat_sayisi",
        "katsayisi",
        "ortalama_kat",
        "kat",
        "kat_adedi",
        "katadedi",
        "floors",
        "height",
        "yukseklik",
    ):
        for fn in fnames:
            if fn.lower() == fn_cand:
                parsed = parse_floor_count(feat[fn])
                if parsed is not None:
                    return parsed
    return 3


def _extract_feature_label(feat, lang: Optional[str] = None) -> str:
    """Read optional building usage or name from feature attributes."""
    fnames = feat.fields().names()
    for cand in ("arazi_kullanim_tanimi", "kullanim", "fonksiyon", "ad", "name", "tucbs_sinifi", "use", "building"):
        for fn in fnames:
            if fn.lower() == cand:
                v = feat[fn]
                if v not in (None, ""):
                    txt = str(v).strip()
                    if txt and txt.upper() not in ("NULL", "NONE"):
                        return txt[:18]
    return tr_text("default_bldg_label", lang)


def sample_profile_between_points(
    pt_a: QgsPointXY,
    pt_b: QgsPointXY,
    title: Optional[str] = None,
    source_mode: str = "auto",  # "auto", "dem", "contours", "dem_slope", "preset"
    step_meters: float = 2.0,
    vertical_exaggeration: float = 1.0,
    dem_layer: Optional[QgsRasterLayer] = None,
    slope_layer: Optional[QgsRasterLayer] = None,
    contour_layer: Optional[QgsVectorLayer] = None,
    contour_elev_field: Optional[str] = None,
    building_layer: Optional[QgsVectorLayer] = None,
    building_floors_field: Optional[str] = None,
    road_layer: Optional[QgsVectorLayer] = None,
    look_mode: str = "auto",  # "auto", "left", "right", "both", "cut_only"
    look_depth: float = 25.0,
    auto_detect_layers: bool = True,
    include_placeholder_trees: bool = False,
    language: Optional[str] = None,
) -> UrbanProfile:
    """Sample topography, buildings, and roads along A->B line and look corridor."""
    use_lang = normalize_lang(language or get_language())
    if title is None:
        title = tr_text("default_profile_title", use_lang)
    dx = pt_b.x() - pt_a.x()
    dy = pt_b.y() - pt_a.y()
    total_len = math.hypot(dx, dy)
    if total_len < 1.0:
        total_len = 500.0
        ux, uy = 1.0, 0.0
    else:
        ux, uy = dx / total_len, dy / total_len

    # Sol normal (+90 derece CCW: Batı->Doğu çiziminde Kuzey'e bakar)
    nx, ny = -uy, ux

    def project_point(p: QgsPointXY) -> Tuple[float, float]:
        vx = p.x() - pt_a.x()
        vy = p.y() - pt_a.y()
        return (vx * ux + vy * uy, vx * nx + vy * ny)

    # Otomatik katman tespiti (sadece UI dışından/programatik çağrıda istenirse)
    if auto_detect_layers:
        if source_mode in ("auto", "dem", "dem_slope") and dem_layer is None:
            dem_layer = find_dem_raster_layer()
        if source_mode in ("auto", "dem_slope") and slope_layer is None:
            slope_layer = find_slope_raster_layer()
        if source_mode in ("auto", "contours") and contour_layer is None:
            contour_layer = find_contour_vector_layer()
        if building_layer is None:
            building_layer = find_building_polygon_layer()
        if road_layer is None:
            road_layer = find_road_layer()

    if contour_layer and not contour_elev_field:
        contour_elev_field = detect_elevation_field(contour_layer)
    if building_layer and not building_floors_field:
        building_floors_field = detect_building_floors_field(building_layer)

    # 1. Zemin ve Eğim Profili Örnekleme
    terrain_pts: List[Tuple[float, float]] = []
    slope_pts: List[Tuple[float, float]] = []
    contour_crossings: List[Tuple[float, float]] = []
    source_name = tr_text("preset_source_fallback", use_lang)
    actual_source_type = "preset"

    use_contours = (source_mode == "contours" or (source_mode == "auto" and contour_layer and not dem_layer))
    use_dem = (source_mode in ("dem", "dem_slope") or (source_mode == "auto" and dem_layer))

    if use_contours and contour_layer and contour_layer.isValid() and contour_elev_field:
        terrain_pts, slope_pts = sample_profile_from_contours(
            pt_a=pt_a,
            pt_b=pt_b,
            contour_layer=contour_layer,
            elev_field=contour_elev_field,
            step_meters=step_meters,
            out_crossings=contour_crossings,
        )
        source_name = tr_text(
            "contours_source_fmt",
            use_lang,
            name=contour_layer.name(),
            field=contour_elev_field,
            cnt=len(contour_crossings),
        )
        actual_source_type = "contours"

    elif use_dem and dem_layer and dem_layer.isValid():
        terrain_pts, slope_pts = sample_profile_from_dem(
            pt_a=pt_a,
            pt_b=pt_b,
            dem_layer=dem_layer,
            slope_layer=slope_layer,
            step_meters=step_meters,
        )
        if slope_layer:
            source_name = tr_text("dem_slope_source_fmt", use_lang, dem=dem_layer.name(), slope=slope_layer.name())
        else:
            source_name = tr_text("dem_source_fmt", use_lang, name=dem_layer.name())
        actual_source_type = "dem_slope" if slope_layer else "dem"

    else:
        num_s = max(20, int(total_len / max(1.0, step_meters)))
        dx_m = total_len / float(num_s - 1)
        for i in range(num_s):
            x = i * dx_m
            t = x / total_len
            z = 120.0 + 35.0 * math.sin(t * math.pi * 1.5) + 10.0 * math.cos(t * 4.0)
            terrain_pts.append((round(x, 2), round(z, 2)))
        source_name = tr_text("preset_source_fallback", use_lang)
        actual_source_type = "preset"

    resolved_look_dir = look_mode
    prof = UrbanProfile(
        title=title,
        scale_label="1/1000",
        total_length=total_len,
        terrain_points=terrain_pts,
        slope_points=slope_pts,
        sky_theme="sunset",
        earth_style="soil_hatch",
        vertical_exaggeration=vertical_exaggeration,
        source_layer_name=source_name,
        source_type=actual_source_type,
        look_direction=resolved_look_dir,
        look_depth=look_depth,
        contour_crossings=contour_crossings,
        language=use_lang,
    )

    section_geom = QgsGeometry.fromPolylineXY([pt_a, pt_b])

    # 2. Binaları Kesiştir & Bakış Yönü Silüetini Çıkar (Ortogonal İzdüşüm ile %100 Harita Uyumu)
    if building_layer and building_layer.isValid():
        proj = QgsProject.instance()
        b_crs = building_layer.crs()
        p_crs = proj.crs()
        need_b_xform = (p_crs.isValid() and b_crs.isValid() and p_crs != b_crs)
        xform_bldg = QgsCoordinateTransform(p_crs, b_crs, proj) if need_b_xform else None
        xform_back = QgsCoordinateTransform(b_crs, p_crs, proj) if need_b_xform else None

        sec_geom_bldg = QgsGeometry(section_geom)
        if xform_bldg:
            sec_geom_bldg.transform(xform_bldg)

        cut_feat_ids = set()

        # A) Doğrudan Kesilen Binalar (Ön Plan)
        req_cut = QgsFeatureRequest().setFilterRect(sec_geom_bldg.boundingBox())
        for feat in building_layer.getFeatures(req_cut):
            geom = feat.geometry()
            if not geom or geom.isEmpty():
                continue
            if geom.intersects(sec_geom_bldg):
                inter = geom.intersection(sec_geom_bldg)
                if inter.isEmpty():
                    continue
                floors = _extract_feature_floors(feat, building_floors_field)
                b_lbl = _extract_feature_label(feat, use_lang)

                for part in inter.asGeometryCollection():
                    pts_p = [xform_back.transform(QgsPointXY(v)) if xform_back else QgsPointXY(v) for v in part.vertices()]
                    if not pts_p:
                        continue
                    ts = [project_point(pt)[0] for pt in pts_p]
                    b_start = max(0.0, min(ts))
                    b_end = min(total_len, max(ts))
                    if b_end - b_start < 0.8:
                        continue
                    b_mid = (b_start + b_end) / 2.0
                    z_s = prof.get_elevation_at(b_start)
                    z_m = prof.get_elevation_at(b_mid)
                    z_e = prof.get_elevation_at(b_end)
                    prof.add_building(BuildingMass(
                        start_dist=b_start,
                        end_dist=b_end,
                        ground_elevation=z_m,
                        ground_min_elevation=min(z_s, z_m, z_e),
                        floors=floors,
                        label=b_lbl,
                        is_cut=True,
                        depth_dist=0.0,
                    ))
                    cut_feat_ids.add(feat.id())

        # B) Bakış Yönü / Sokak Silüeti Koridoru
        def _collect_corridor(side_key: str) -> List[BuildingMass]:
            if look_depth <= 0.5:
                return []
            if side_key == "left":
                pa_e = QgsPointXY(pt_a.x() + nx * look_depth, pt_a.y() + ny * look_depth)
                pb_e = QgsPointXY(pt_b.x() + nx * look_depth, pt_b.y() + ny * look_depth)
                c_geom = QgsGeometry.fromPolygonXY([[pt_a, pt_b, pb_e, pa_e, pt_a]])
            elif side_key == "right":
                pa_e = QgsPointXY(pt_a.x() - nx * look_depth, pt_a.y() - ny * look_depth)
                pb_e = QgsPointXY(pt_b.x() - nx * look_depth, pt_b.y() - ny * look_depth)
                c_geom = QgsGeometry.fromPolygonXY([[pt_a, pa_e, pb_e, pt_b, pt_a]])
            else:  # "both"
                la = QgsPointXY(pt_a.x() + nx * look_depth, pt_a.y() + ny * look_depth)
                lb = QgsPointXY(pt_b.x() + nx * look_depth, pt_b.y() + ny * look_depth)
                rb = QgsPointXY(pt_b.x() - nx * look_depth, pt_b.y() - ny * look_depth)
                ra = QgsPointXY(pt_a.x() - nx * look_depth, pt_a.y() - ny * look_depth)
                c_geom = QgsGeometry.fromPolygonXY([[la, lb, rb, ra, la]])

            c_geom_b = QgsGeometry(c_geom)
            if xform_bldg:
                c_geom_b.transform(xform_bldg)

            found_sil: List[BuildingMass] = []
            req_sil = QgsFeatureRequest().setFilterRect(c_geom_b.boundingBox())
            for feat in building_layer.getFeatures(req_sil):
                if feat.id() in cut_feat_ids:
                    continue
                geom = feat.geometry()
                if not geom or geom.isEmpty() or not geom.intersects(c_geom_b):
                    continue
                clip = geom.intersection(c_geom_b)
                if clip.isEmpty():
                    continue
                floors = _extract_feature_floors(feat, building_floors_field)
                b_lbl = _extract_feature_label(feat, use_lang)

                for part in clip.asGeometryCollection():
                    pts_p = [xform_back.transform(QgsPointXY(v)) if xform_back else QgsPointXY(v) for v in part.vertices()]
                    if not pts_p:
                        continue
                    proj_res = [project_point(pt) for pt in pts_p]
                    ts = [r[0] for r in proj_res]
                    ss = [abs(r[1]) for r in proj_res]
                    b_start = max(0.0, min(ts))
                    b_end = min(total_len, max(ts))
                    if b_end - b_start < 1.0:
                        continue
                    depth_d = min(ss) if ss else look_depth * 0.5
                    b_mid = (b_start + b_end) / 2.0
                    z_s = prof.get_elevation_at(b_start)
                    z_m = prof.get_elevation_at(b_mid)
                    z_e = prof.get_elevation_at(b_end)
                    found_sil.append(BuildingMass(
                        start_dist=b_start,
                        end_dist=b_end,
                        ground_elevation=z_m,
                        ground_min_elevation=min(z_s, z_m, z_e),
                        floors=floors,
                        label=b_lbl,
                        facade_color="#e2e8f0",
                        outline_color="#64748b",
                        is_cut=False,
                        depth_dist=depth_d,
                    ))
            return found_sil

        sil_bldgs: List[BuildingMass] = []
        if look_mode in ("left", "right", "both"):
            sil_bldgs = _collect_corridor(look_mode)
            prof.look_direction = look_mode
        elif look_mode == "auto" and not prof.buildings:
            # Sokak/boşluk ekseni boyunca çizildiyse önce Sol/Kuzey tarafı, boşsa Sağ/Güney tarafı oku
            sil_left = _collect_corridor("left")
            if sil_left:
                sil_bldgs = sil_left
                prof.look_direction = "left"
            else:
                sil_right = _collect_corridor("right")
                if sil_right:
                    sil_bldgs = sil_right
                    prof.look_direction = "right"
                else:
                    prof.look_direction = "auto"

        for sb in sil_bldgs:
            prof.add_building(sb)

    elif actual_source_type == "preset":
        # Sadece bina katmanı hiç yoksa (şablon modunda) temsili stüdyo kütleleri ekle
        step_bldg = total_len / 7.0
        for b_idx in range(1, 6):
            b_center = b_idx * step_bldg
            b_w = 20.0
            fl = 3 if b_idx % 2 == 0 else 4
            prof.add_building(BuildingMass(
                start_dist=b_center - b_w / 2,
                end_dist=b_center + b_w / 2,
                ground_elevation=prof.get_elevation_at(b_center),
                floors=fl,
                label=tr_text("default_bldg_label", use_lang),
            ))

    if prof.buildings and prof.total_length > 800.0:
        prof.cluster_buildings(
            max_gap=max(16.0, prof.total_length / 140.0),
            min_width=max(22.0, prof.total_length / 100.0),
        )

    # 3. Yolları Kesiştir (CRS Dönüşümlü, Ortogonal İzdüşüm & Güvenli Öznitelik Okuma)
    if road_layer and road_layer.isValid():
        proj = QgsProject.instance()
        r_crs = road_layer.crs()
        p_crs = proj.crs()
        need_r_xform = (p_crs.isValid() and r_crs.isValid() and p_crs != r_crs)
        xform_road = QgsCoordinateTransform(p_crs, r_crs, proj) if need_r_xform else None
        xform_r_back = QgsCoordinateTransform(r_crs, p_crs, proj) if need_r_xform else None

        sec_geom_road = QgsGeometry(section_geom)
        if xform_road:
            sec_geom_road.transform(xform_road)

        req = QgsFeatureRequest().setFilterRect(sec_geom_road.boundingBox())
        for feat in road_layer.getFeatures(req):
            geom = feat.geometry()
            if not geom or geom.isEmpty():
                continue
            if geom.intersects(sec_geom_road):
                inter = geom.intersection(sec_geom_road)
                if not inter.isEmpty():
                    pts_r = [xform_r_back.transform(QgsPointXY(v)) if xform_r_back else QgsPointXY(v) for v in inter.vertices()]
                    if not pts_r:
                        continue
                    ts_r = [project_point(pt)[0] for pt in pts_r]
                    d_road = max(0.0, min(total_len, sum(ts_r) / len(ts_r)))

                    r_name = tr_text("default_road_name", use_lang)
                    field_names = [f.name() for f in feat.fields()]
                    for cand_fn in ("ad", "name", "yol_adi", "cadde_sokak", "yol_tanimi", "tanim", "tip", "layer"):
                        found = False
                        for fn in field_names:
                            if cand_fn == fn.lower():
                                val = feat[fn]
                                if val not in (None, ""):
                                    r_name = str(val)
                                    found = True
                                    break
                        if found:
                            break

                    r_width = 12.0
                    for w_cand in ("genislik", "width", "kirmizi_cizgi", "yol_genisligi"):
                        found_w = False
                        for fn in field_names:
                            if w_cand == fn.lower():
                                try:
                                    w_val = float(feat[fn])
                                    if 3.0 <= w_val <= 60.0:
                                        r_width = w_val
                                        found_w = True
                                        break
                                except (ValueError, TypeError):
                                    pass
                        if found_w:
                            break

                    prof.add_road(RoadIncision(
                        center_dist=d_road,
                        width=r_width,
                        elevation=prof.get_elevation_at(d_road),
                        name=r_name,
                    ))

    # 4. Ağaç Kümeleri (Yalnızca kullanıcı açıkça isterse veya tamamen şablon modundaysa ekle)
    has_real_bldg_layer = bool(building_layer and building_layer.isValid())
    has_real_road_layer = bool(road_layer and road_layer.isValid())
    if include_placeholder_trees or (actual_source_type == "preset" and not has_real_bldg_layer and not has_real_road_layer):
        veg_spacing = total_len / 9.0
        for v_idx in range(1, 9):
            vx = v_idx * veg_spacing + (v_idx % 2 * 10 - 5)
            if not any(abs(vx - b.center_dist) < b.width / 2 + 6 for b in prof.buildings):
                prof.add_vegetation(VegetationCluster(
                    center_dist=vx,
                    ground_elevation=prof.get_elevation_at(vx),
                    width=16.0,
                    tree_count=3 if v_idx % 2 == 0 else 4,
                ))

    return prof
