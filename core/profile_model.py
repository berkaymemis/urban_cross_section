# -*- coding: utf-8 -*-
"""UrbanCrossSection — Kentsel Silüet ve Topografya A-B Kesiti Veri Modeli (core/profile_model.py).

Saf Python: Hiçbir qgis veya PyQt bağımlılığı içermez.
1/1000 A-A' ve B-B' kentsel kesitleri, arazi eğimi, bina kütleleri ve silüet modellemesi.
"""

import math
from typing import List, Dict, Any, Optional
from .i18n import get_language, normalize_lang, retranslate_profile_inplace, tr_text


class BuildingMass:
    """Kesit hattı üzerinde veya bakış silüeti koridorunda yer alan mimari yapı kütlesi."""

    def __init__(
        self,
        start_dist: float,
        end_dist: float,
        ground_elevation: float,
        floors: int = 4,
        floor_height: float = 3.0,
        roof_style: str = "flat",  # "flat", "sloped", "terrace"
        label: Optional[str] = None,
        facade_color: str = "#ffffff",
        outline_color: str = "#334155",
        ground_min_elevation: Optional[float] = None,
        is_cut: bool = True,
        depth_dist: float = 0.0,
    ):
        self.start_dist = float(start_dist)
        self.end_dist = float(end_dist)
        self.width = max(1.0, self.end_dist - self.start_dist)
        self.center_dist = (self.start_dist + self.end_dist) / 2.0
        self.ground_elevation = float(ground_elevation)
        self.ground_min_elevation = (
            float(ground_min_elevation) if ground_min_elevation is not None else float(ground_elevation)
        )
        self.floors = max(1, int(floors))
        self.floor_height = float(floor_height)
        self.height = self.floors * self.floor_height
        self.top_elevation = self.ground_elevation + self.height
        self.roof_style = roof_style
        self.label = label if label is not None else tr_text("default_bldg_label")
        self.facade_color = facade_color
        self.outline_color = outline_color
        self.is_cut = bool(is_cut)
        self.depth_dist = max(0.0, float(depth_dist))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_dist": self.start_dist,
            "end_dist": self.end_dist,
            "width": self.width,
            "ground_elevation": self.ground_elevation,
            "ground_min_elevation": self.ground_min_elevation,
            "floors": self.floors,
            "floor_height": self.floor_height,
            "height": self.height,
            "top_elevation": self.top_elevation,
            "roof_style": self.roof_style,
            "label": self.label,
            "is_cut": self.is_cut,
            "depth_dist": self.depth_dist,
        }


class VegetationCluster:
    """Kesit üzerindeki ağaç ve yeşil doku kümesi."""

    def __init__(
        self,
        center_dist: float,
        ground_elevation: float,
        width: float = 8.0,
        tree_count: int = 3,
        tree_height: float = 7.0,
        tree_type: str = "deciduous",  # "deciduous" (yapraklı), "pine" (iğne yapraklı/çam)
    ):
        self.center_dist = float(center_dist)
        self.ground_elevation = float(ground_elevation)
        self.width = float(width)
        self.tree_count = max(1, int(tree_count))
        self.tree_height = float(tree_height)
        self.tree_type = tree_type

    def to_dict(self) -> Dict[str, Any]:
        return {
            "center_dist": self.center_dist,
            "ground_elevation": self.ground_elevation,
            "width": self.width,
            "tree_count": self.tree_count,
            "tree_height": self.tree_height,
            "tree_type": self.tree_type,
        }


class RoadIncision:
    """Kesitin kestiği yol / sokak platformu."""

    def __init__(
        self,
        center_dist: float,
        width: float,
        elevation: float,
        name: Optional[str] = None,
    ):
        self.center_dist = float(center_dist)
        self.width = float(width)
        self.elevation = float(elevation)
        self.name = name if name is not None else tr_text("default_road_name")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "center_dist": self.center_dist,
            "width": self.width,
            "elevation": self.elevation,
            "name": self.name,
        }


class UrbanProfile:
    """1/1000 Kentsel Silüet & Topografya A-A' / B-B' Kesiti Master Modeli."""

    def __init__(
        self,
        title: Optional[str] = None,
        scale_label: str = "1/1000",
        total_length: float = 600.0,
        terrain_points: Optional[List[tuple]] = None,
        slope_points: Optional[List[tuple]] = None,
        buildings: Optional[List[BuildingMass]] = None,
        vegetation: Optional[List[VegetationCluster]] = None,
        roads: Optional[List[RoadIncision]] = None,
        sky_theme: str = "sunset",  # "sunset", "golden_hour", "daylight", "blueprint"
        earth_style: str = "soil_hatch",  # "soil_hatch", "rock_hatch", "minimal_gray"
        vertical_exaggeration: float = 1.0,
        source_layer_name: Optional[str] = None,
        source_type: str = "preset",  # "dem", "contours", "dem_slope", "preset"
        critical_slope_threshold: float = 20.0,
        description: str = "",
        look_direction: str = "auto",  # "auto", "left", "right", "both", "cut_only"
        look_depth: float = 25.0,
        contour_crossings: Optional[List[tuple]] = None,
        language: Optional[str] = None,
    ):
        self.language = normalize_lang(language or get_language())
        self.title = title if title is not None else tr_text("default_profile_title", self.language)
        self.scale_label = scale_label
        self.total_length = max(10.0, float(total_length))
        self.terrain_points = terrain_points or []
        self.slope_points = slope_points or []
        self.buildings = buildings or []
        self.vegetation = vegetation or []
        self.roads = roads or []
        self.sky_theme = sky_theme
        self.earth_style = earth_style
        self.vertical_exaggeration = max(1.0, float(vertical_exaggeration))
        self.source_layer_name = (
            source_layer_name if source_layer_name is not None else tr_text("default_source_preset", self.language)
        )
        self.source_type = source_type
        self.critical_slope_threshold = float(critical_slope_threshold)
        self.description = description
        self.look_direction = look_direction
        self.look_depth = max(0.0, float(look_depth))
        self.contour_crossings = contour_crossings or []
        self.unclustered_buildings: Optional[List[BuildingMass]] = None

        # Arazi noktaları boşsa varsayılan topografya oluştur
        if not self.terrain_points:
            self._generate_default_terrain()

        # Eğim noktaları boşsa otomatik hesapla
        if not self.slope_points and self.terrain_points:
            self._compute_slope_profile()

    def _generate_default_terrain(self):
        """Doğal yamaç ve tepe morfolojisi üreten varsayılan topografya."""
        points = []
        num_pts = 60
        dx = self.total_length / float(num_pts - 1)
        for i in range(num_pts):
            x = i * dx
            # Çift tepeli ve vadili zengin stüdyo topografyası
            z = 110.0 + 38.0 * math.sin(x / self.total_length * math.pi * 1.4) + 12.0 * math.cos(x / 120.0)
            points.append((round(x, 2), round(z, 2)))
        self.terrain_points = points

    @property
    def min_elevation(self) -> float:
        if not self.terrain_points:
            return 0.0
        return min(p[1] for p in self.terrain_points)

    @property
    def max_elevation(self) -> float:
        if not self.terrain_points:
            return 100.0
        top_pts = [p[1] for p in self.terrain_points]
        top_bldgs = [b.top_elevation for b in self.buildings]
        return max(top_pts + top_bldgs) if top_bldgs else max(top_pts)

    @property
    def elevation_span(self) -> float:
        return max(10.0, self.max_elevation - self.min_elevation)

    def get_elevation_at(self, dist: float) -> float:
        """Belirtilen mesafedeki zemin kotunu doğrusal enterpolasyonla bulur."""
        if not self.terrain_points:
            return 100.0
        if dist <= self.terrain_points[0][0]:
            return self.terrain_points[0][1]
        if dist >= self.terrain_points[-1][0]:
            return self.terrain_points[-1][1]

        for i in range(len(self.terrain_points) - 1):
            x0, z0 = self.terrain_points[i]
            x1, z1 = self.terrain_points[i + 1]
            if x0 <= dist <= x1:
                t = (dist - x0) / max(0.001, (x1 - x0))
                return z0 + t * (z1 - z0)
        return self.terrain_points[-1][1]

    def add_building(self, building: BuildingMass):
        self.buildings.append(building)
        self.buildings.sort(key=lambda b: b.start_dist)

    def add_vegetation(self, veg: VegetationCluster):
        self.vegetation.append(veg)

    def add_road(self, road: RoadIncision):
        self.roads.append(road)

    def _compute_slope_profile(self):
        """Arazi kotlarından her nokta için yerel eğim yüzdesini hesaplar."""
        if not self.terrain_points or len(self.terrain_points) < 2:
            self.slope_points = [(0.0, 0.0)]
            return

        slopes = []
        n = len(self.terrain_points)
        for i in range(n):
            x_i, z_i = self.terrain_points[i]
            if i == 0:
                x_next, z_next = self.terrain_points[1]
                dx = max(0.1, x_next - x_i)
                slp = abs(z_next - z_i) / dx * 100.0
            elif i == n - 1:
                x_prev, z_prev = self.terrain_points[n - 2]
                dx = max(0.1, x_i - x_prev)
                slp = abs(z_i - z_prev) / dx * 100.0
            else:
                x_prev, z_prev = self.terrain_points[i - 1]
                x_next, z_next = self.terrain_points[i + 1]
                dx = max(0.2, x_next - x_prev)
                slp = abs(z_next - z_prev) / dx * 100.0
            slopes.append((x_i, round(slp, 2)))
        self.slope_points = slopes

    def get_slope_at(self, dist: float) -> float:
        """Belirtilen mesafedeki eğim yüzdesini (% cinsinden) döndürür."""
        if not self.slope_points:
            return 0.0
        if dist <= self.slope_points[0][0]:
            return self.slope_points[0][1]
        if dist >= self.slope_points[-1][0]:
            return self.slope_points[-1][1]

        for i in range(len(self.slope_points) - 1):
            x0, s0 = self.slope_points[i]
            x1, s1 = self.slope_points[i + 1]
            if x0 <= dist <= x1:
                t = (dist - x0) / max(0.001, (x1 - x0))
                return s0 + t * (s1 - s0)
        return self.slope_points[-1][1]

    def get_statistics(self) -> Dict[str, Any]:
        """Kentsel silüet kesitinin imar mevzuatı ve topografik istatistiklerini üretir."""
        if not self.terrain_points:
            return {}

        min_z = self.min_elevation
        max_z = max(p[1] for p in self.terrain_points)
        dz = max_z - min_z

        slope_vals = [s[1] for s in self.slope_points] if self.slope_points else [0.0]
        max_slope = max(slope_vals) if slope_vals else 0.0
        avg_slope = sum(slope_vals) / max(1, len(slope_vals))

        # Kritik eğim eşiği (> %20 imar kısıtlaması)
        crit_len = 0.0
        if len(self.slope_points) >= 2:
            for i in range(len(self.slope_points) - 1):
                x0, s0 = self.slope_points[i]
                x1, s1 = self.slope_points[i + 1]
                mid_s = (s0 + s1) / 2.0
                if mid_s >= self.critical_slope_threshold:
                    crit_len += (x1 - x0)

        crit_ratio = (crit_len / max(1.0, self.total_length)) * 100.0

        cut_cnt = sum(1 for b in self.buildings if getattr(b, "is_cut", True))
        sil_cnt = sum(1 for b in self.buildings if not getattr(b, "is_cut", True))

        return {
            "title": self.title,
            "total_length": round(self.total_length, 1),
            "min_elevation": round(min_z, 2),
            "max_elevation": round(max_z, 2),
            "elevation_delta": round(dz, 2),
            "start_elevation": round(self.terrain_points[0][1], 2),
            "end_elevation": round(self.terrain_points[-1][1], 2),
            "max_slope_pct": round(max_slope, 1),
            "avg_slope_pct": round(avg_slope, 1),
            "critical_slope_length": round(crit_len, 1),
            "critical_slope_ratio": round(crit_ratio, 1),
            "has_critical_slope": crit_ratio > 0.0,
            "building_count": len(self.buildings),
            "cut_building_count": cut_cnt,
            "silhouette_building_count": sil_cnt,
            "tree_cluster_count": len(self.vegetation),
            "road_count": len(self.roads),
            "source_layer_name": self.source_layer_name,
            "source_type": self.source_type,
            "vertical_exaggeration": self.vertical_exaggeration,
            "look_direction": self.look_direction,
            "look_depth": self.look_depth,
        }

    def calculate_slopes(self) -> List[Dict[str, Any]]:
        """Önemli yamaç segmentlerindeki eğim yüzdelerini hesaplar."""
        slopes = []
        step = max(40.0, self.total_length / 7.0)
        cur = 0.0
        while cur + step <= self.total_length + 0.1:
            x0 = cur
            x1 = min(self.total_length, cur + step)
            z0 = self.get_elevation_at(x0)
            z1 = self.get_elevation_at(x1)
            dx = max(0.1, x1 - x0)
            dz = z1 - z0
            slope_pct = (dz / dx) * 100.0
            mid_d = (x0 + x1) / 2.0
            slopes.append({
                "start_dist": x0,
                "end_dist": x1,
                "mid_dist": mid_d,
                "mid_elev": (z0 + z1) / 2.0,
                "slope_pct": round(slope_pct, 1),
                "is_critical": abs(slope_pct) >= self.critical_slope_threshold,
            })
            cur += step
        return slopes

    def cluster_buildings(self, max_gap: float = 18.0, min_width: float = 20.0):
        """Uzun kesitlerde (örn. >800m) aynı türdeki yakın binaları kentsel yapı adası / blok olarak birleştirir.
        Doğrudan kesilen (is_cut=True) ve silüet (is_cut=False) kütlelerini birbirinden ayrı gruplar.
        """
        if not self.buildings:
            return

        if self.unclustered_buildings is None:
            self.unclustered_buildings = list(self.buildings)

        merged_all: List[BuildingMass] = []
        for cut_flag in (False, True):
            subset = sorted(
                [b for b in self.buildings if getattr(b, "is_cut", True) == cut_flag],
                key=lambda b: b.start_dist,
            )
            if not subset:
                continue

            cur_group = [subset[0]]
            for b in subset[1:]:
                prev_end = max(x.end_dist for x in cur_group)
                if b.start_dist - prev_end <= max_gap:
                    cur_group.append(b)
                else:
                    merged_all.append(self._make_merged_block(cur_group, min_width, is_cut=cut_flag))
                    cur_group = [b]
            if cur_group:
                merged_all.append(self._make_merged_block(cur_group, min_width, is_cut=cut_flag))

        self.buildings = sorted(merged_all, key=lambda b: b.start_dist)

    def _make_merged_block(self, group: List[BuildingMass], min_width: float, is_cut: bool = True) -> BuildingMass:
        start_d = min(b.start_dist for b in group)
        end_d = max(b.end_dist for b in group)
        fl = max(b.floors for b in group)
        fh = max(b.floor_height for b in group)

        if end_d - start_d < min_width:
            mid = (start_d + end_d) / 2.0
            start_d = max(0.0, mid - min_width / 2.0)
            end_d = min(self.total_length, mid + min_width / 2.0)

        mid_d = (start_d + end_d) / 2.0
        g_elev = self.get_elevation_at(mid_d)
        cand_mins = [self.get_elevation_at(start_d), g_elev, self.get_elevation_at(end_d)]
        cand_mins.extend(
            b.ground_min_elevation
            for b in group
            if getattr(b, "ground_min_elevation", None) is not None
        )
        g_min = min(cand_mins)
        lbl = (
            tr_text("urban_block_label", getattr(self, "language", "en"), floors=fl)
            if len(group) > 1
            else group[0].label
        )
        min_depth = min(getattr(b, "depth_dist", 0.0) for b in group)
        return BuildingMass(
            start_dist=start_d,
            end_dist=end_d,
            ground_elevation=g_elev,
            ground_min_elevation=g_min,
            floors=fl,
            floor_height=fh,
            label=lbl,
            facade_color=group[0].facade_color,
            outline_color=group[0].outline_color,
            is_cut=is_cut,
            depth_dist=min_depth,
        )

    def create_segment(self, start_dist: float, end_dist: float, seg_index: int = 1, total_segs: int = 1) -> "UrbanProfile":
        """Kesitin belirtilen mesafe aralığını (start_dist - end_dist) bağımsız 1/1000 kentsel profil olarak dilimler."""
        s_d = max(0.0, float(start_dist))
        e_d = min(self.total_length, float(end_dist))
        seg_len = max(10.0, e_d - s_d)

        # 1. Arazi noktaları
        seg_terrain = [(0.0, self.get_elevation_at(s_d))]
        for x, z in self.terrain_points:
            if s_d < x < e_d:
                seg_terrain.append((round(x - s_d, 2), round(z, 2)))
        seg_terrain.append((round(seg_len, 2), self.get_elevation_at(e_d)))
        seen_x = set()
        uniq_terrain = []
        for p in sorted(seg_terrain, key=lambda p: p[0]):
            rk = round(p[0], 2)
            if rk not in seen_x:
                seen_x.add(rk)
                uniq_terrain.append(p)

        # 2. Eğim noktaları
        seg_slopes = [(0.0, self.get_slope_at(s_d))]
        for x, s in self.slope_points:
            if s_d < x < e_d:
                seg_slopes.append((round(x - s_d, 2), round(s, 2)))
        seg_slopes.append((round(seg_len, 2), self.get_slope_at(e_d)))
        seen_s = set()
        uniq_slopes = []
        for p in sorted(seg_slopes, key=lambda p: p[0]):
            rk = round(p[0], 2)
            if rk not in seen_s:
                seen_s.add(rk)
                uniq_slopes.append(p)

        # 3. Binalar (Kesişenler ve silüet kütleleri - ham binalardan dilimlenir)
        source_bldgs = self.unclustered_buildings if self.unclustered_buildings is not None else self.buildings
        seg_bldgs = []
        for b in source_bldgs:
            o_start = max(b.start_dist, s_d)
            o_end = min(b.end_dist, e_d)
            if o_end - o_start >= 1.0:
                rel_start = o_start - s_d
                rel_end = o_end - s_d
                mid = (rel_start + rel_end) / 2.0
                z_s = self.get_elevation_at(o_start)
                z_m = self.get_elevation_at(s_d + mid)
                z_e = self.get_elevation_at(o_end)
                orig_min = getattr(b, "ground_min_elevation", None)
                seg_min = min(z_s, z_m, z_e)
                if orig_min is not None and o_start <= b.start_dist + 0.01 and o_end >= b.end_dist - 0.01:
                    seg_min = min(seg_min, orig_min)
                seg_bldgs.append(BuildingMass(
                    start_dist=rel_start,
                    end_dist=rel_end,
                    ground_elevation=z_m,
                    ground_min_elevation=seg_min,
                    floors=b.floors,
                    floor_height=b.floor_height,
                    roof_style=b.roof_style,
                    label=b.label,
                    facade_color=b.facade_color,
                    outline_color=b.outline_color,
                    is_cut=getattr(b, "is_cut", True),
                    depth_dist=getattr(b, "depth_dist", 0.0),
                ))

        # 4. Vejetasyon
        seg_veg = []
        for v in self.vegetation:
            if s_d <= v.center_dist <= e_d:
                rel_center = v.center_dist - s_d
                seg_veg.append(VegetationCluster(
                    center_dist=rel_center,
                    ground_elevation=self.get_elevation_at(v.center_dist),
                    width=v.width,
                    tree_count=v.tree_count,
                    tree_height=v.tree_height,
                    tree_type=v.tree_type,
                ))

        # 5. Yollar
        seg_roads = []
        for r in self.roads:
            if s_d <= r.center_dist <= e_d:
                seg_roads.append(RoadIncision(
                    center_dist=r.center_dist - s_d,
                    width=r.width,
                    elevation=r.elevation,
                    name=r.name,
                ))

        # 6. İzoips kesişimleri
        seg_crossings = [
            (round(cx - s_d, 2), cz)
            for cx, cz in getattr(self, "contour_crossings", [])
            if s_d <= cx <= e_d
        ]

        seg_lang = getattr(self, "language", "en")
        base_title = self.title.split(" [Bölüm")[0].split(" [Sheet")[0]
        if seg_lang == "tr":
            seg_title = f"{base_title} [Bölüm {seg_index}/{total_segs}: {int(s_d)}m - {int(e_d)}m]"
        else:
            seg_title = f"{base_title} [Sheet {seg_index}/{total_segs}: {int(s_d)}m - {int(e_d)}m]"

        return UrbanProfile(
            title=seg_title,
            scale_label="1/1000",
            total_length=seg_len,
            terrain_points=uniq_terrain,
            slope_points=uniq_slopes,
            buildings=seg_bldgs,
            vegetation=seg_veg,
            roads=seg_roads,
            sky_theme=self.sky_theme,
            earth_style=self.earth_style,
            vertical_exaggeration=self.vertical_exaggeration,
            source_layer_name=self.source_layer_name,
            source_type=self.source_type,
            critical_slope_threshold=self.critical_slope_threshold,
            description=self.description,
            look_direction=self.look_direction,
            look_depth=self.look_depth,
            contour_crossings=seg_crossings,
            language=seg_lang,
        )

    def get_segments(self, segment_length: float = 700.0) -> List["UrbanProfile"]:
        """Kesiti standart jüri paftası uzunluğunda (varsayılan 700m) ardışık alt bölümlere ayırır."""
        if self.total_length <= segment_length:
            return [self]

        num_segs = max(1, math.ceil(self.total_length / segment_length))
        seg_w = self.total_length / float(num_segs)
        segments = []
        for i in range(num_segs):
            s_d = i * seg_w
            e_d = min(self.total_length, (i + 1) * seg_w)
            segments.append(self.create_segment(s_d, e_d, seg_index=i + 1, total_segs=num_segs))
        return segments


def pchip_interpolate_series(
    control_points: List[tuple],
    eval_x_list: List[float],
) -> List[tuple]:
    """Eşyükselti eğrileri kesişim noktalarından türetilen kontrol noktaları arasında

    Fritsch-Carlson Monotonik Kübik Hermite Enterpolasyonu (PCHIP) uygular.
    Standart kübik spline'ların aksine yapay dalgalanma (overshoot) ve yapay çökme üretmez;
    topoğrafik eğriler arasında gerçekçi ve pürüzsüz vadi-tepe morfolojisi sağlar.
    """
    if not control_points:
        return [(x, 100.0) for x in eval_x_list]

    # Tekil ve sıralı kontrol noktaları
    sorted_pts = sorted(control_points, key=lambda p: p[0])
    # Aynı x koordinatına denk gelen mükerrerleri filtrele
    unique_pts = [sorted_pts[0]]
    for p in sorted_pts[1:]:
        if abs(p[0] - unique_pts[-1][0]) > 1e-4:
            unique_pts.append(p)

    if len(unique_pts) == 1:
        z_const = unique_pts[0][1]
        return [(round(x, 2), round(z_const, 2)) for x in eval_x_list]

    n = len(unique_pts)
    x = [p[0] for p in unique_pts]
    y = [p[1] for p in unique_pts]

    # 1. Kesen eğimler (secants)
    h = [x[k + 1] - x[k] for k in range(n - 1)]
    delta = [(y[k + 1] - y[k]) / h[k] for k in range(n - 1)]

    # 2. Türevler (tangents)
    d = [0.0] * n
    # Uç noktalar: tek taraflı fark
    d[0] = delta[0]
    d[-1] = delta[-1]

    for k in range(1, n - 1):
        if delta[k - 1] * delta[k] <= 0:
            d[k] = 0.0
        else:
            # Standart harmonik ortalama
            w1 = 2.0 * h[k] + h[k - 1]
            w2 = h[k] + 2.0 * h[k - 1]
            d[k] = (w1 + w2) / (w1 / delta[k - 1] + w2 / delta[k])

    # 3. Fritsch & Carlson Monotonluk Düzeltmesi
    for k in range(n - 1):
        if abs(delta[k]) < 1e-9:
            d[k] = 0.0
            d[k + 1] = 0.0
        else:
            alpha = d[k] / delta[k]
            beta = d[k + 1] / delta[k]
            phi = alpha * alpha + beta * beta
            if phi > 9.0:
                tau = 3.0 / math.sqrt(phi)
                d[k] = tau * alpha * delta[k]
                d[k + 1] = tau * beta * delta[k]

    # 4. İstenen x noktalarında Kübik Hermite Değerlendirmesi
    results = []
    for qx in eval_x_list:
        # Aralık tespiti
        if qx <= x[0]:
            results.append((round(qx, 2), round(y[0], 2)))
            continue
        if qx >= x[-1]:
            results.append((round(qx, 2), round(y[-1], 2)))
            continue

        # İkili arama ile aralık bul
        k = 0
        for i in range(n - 1):
            if x[i] <= qx <= x[i + 1]:
                k = i
                break

        # Kübik Hermite baz fonksiyonları
        hk = h[k]
        t = (qx - x[k]) / hk
        t2 = t * t
        t3 = t2 * t

        h00 = 2.0 * t3 - 3.0 * t2 + 1.0
        h10 = t3 - 2.0 * t2 + t
        h01 = -2.0 * t3 + 3.0 * t2
        h11 = t3 - t2

        interp_y = h00 * y[k] + h10 * hk * d[k] + h01 * y[k + 1] + h11 * hk * d[k + 1]
        results.append((round(qx, 2), round(interp_y, 2)))

    return results


# -----------------------------------------------------------------------------
# Hazır 1/1000 Kentsel Kesit Şablonları (Jüri Örnekleri)
# -----------------------------------------------------------------------------

def preset_profile_hillside_aa(lang: Optional[str] = None) -> UrbanProfile:
    """1:1000 A-A' Urban Hillside & Ridge Sample Profile."""
    use_lang = normalize_lang(lang or get_language())
    prof = UrbanProfile(
        title=tr_text("default_profile_title", use_lang),
        scale_label="1/1000",
        total_length=700.0,
        sky_theme="sunset",
        earth_style="soil_hatch",
        description="Hillside settlement, terraces, massing silhouettes, and green corridors.",
        language=use_lang,
    )

    terrain = [
        (0.0, 115.0),
        (50.0, 120.0),
        (100.0, 127.0),
        (150.0, 138.0),
        (200.0, 154.0),
        (240.0, 160.0),
        (280.0, 159.0),
        (330.0, 146.0),
        (380.0, 136.0),
        (430.0, 128.0),
        (480.0, 122.0),
        (540.0, 124.0),
        (600.0, 130.0),
        (650.0, 134.0),
        (700.0, 137.0),
    ]
    prof.terrain_points = terrain

    buildings = [
        BuildingMass(start_dist=75.0, end_dist=95.0, ground_elevation=prof.get_elevation_at(85.0), floors=3, label="Residential"),
        BuildingMass(start_dist=245.0, end_dist=275.0, ground_elevation=prof.get_elevation_at(260.0), floors=2, label="Summit Facility"),
        BuildingMass(start_dist=420.0, end_dist=445.0, ground_elevation=prof.get_elevation_at(432.5), floors=4, label="Mixed Use"),
        BuildingMass(start_dist=460.0, end_dist=495.0, ground_elevation=prof.get_elevation_at(477.5), floors=5, label="Commercial Hub"),
        BuildingMass(start_dist=570.0, end_dist=590.0, ground_elevation=prof.get_elevation_at(580.0), floors=2, label="Residential"),
        BuildingMass(start_dist=630.0, end_dist=655.0, ground_elevation=prof.get_elevation_at(642.5), floors=4, label="Housing Block"),
        BuildingMass(start_dist=665.0, end_dist=690.0, ground_elevation=prof.get_elevation_at(677.5), floors=4, label="Housing Block"),
    ]
    prof.buildings = buildings

    veg = [
        VegetationCluster(center_dist=30.0, ground_elevation=prof.get_elevation_at(30.0), width=18.0, tree_count=4),
        VegetationCluster(center_dist=125.0, ground_elevation=prof.get_elevation_at(125.0), width=24.0, tree_count=5),
        VegetationCluster(center_dist=175.0, ground_elevation=prof.get_elevation_at(175.0), width=22.0, tree_count=4),
        VegetationCluster(center_dist=215.0, ground_elevation=prof.get_elevation_at(215.0), width=16.0, tree_count=3),
        VegetationCluster(center_dist=305.0, ground_elevation=prof.get_elevation_at(305.0), width=25.0, tree_count=5),
        VegetationCluster(center_dist=355.0, ground_elevation=prof.get_elevation_at(355.0), width=22.0, tree_count=4),
        VegetationCluster(center_dist=525.0, ground_elevation=prof.get_elevation_at(525.0), width=20.0, tree_count=4),
        VegetationCluster(center_dist=610.0, ground_elevation=prof.get_elevation_at(610.0), width=16.0, tree_count=3),
    ]
    prof.vegetation = veg

    roads = [
        RoadIncision(center_dist=110.0, width=12.0, elevation=prof.get_elevation_at(110.0), name="12 m Planned Street"),
        RoadIncision(center_dist=395.0, width=15.0, elevation=prof.get_elevation_at(395.0), name="15 m Collector Avenue"),
        RoadIncision(center_dist=550.0, width=10.0, elevation=prof.get_elevation_at(550.0), name="10 m Local Street"),
    ]
    prof.roads = roads

    if use_lang != "en":
        retranslate_profile_inplace(prof, use_lang)
    return prof


def preset_profile_slope_bb(lang: Optional[str] = None) -> UrbanProfile:
    """1:1000 B-B' Continuous Urban Slope & Valley Sample Profile."""
    use_lang = normalize_lang(lang or get_language())
    prof = UrbanProfile(
        title=tr_text("default_profile_bb_title", use_lang),
        scale_label="1/1000",
        total_length=450.0,
        sky_theme="sunset",
        earth_style="soil_hatch",
        description="Continuous sloped residential fabric across valley transition.",
        language=use_lang,
    )

    terrain = [
        (0.0, 155.0),
        (50.0, 150.0),
        (100.0, 144.0),
        (160.0, 137.0),
        (220.0, 130.0),
        (280.0, 122.0),
        (340.0, 116.0),
        (390.0, 114.0),
        (450.0, 113.0),
    ]
    prof.terrain_points = terrain

    buildings = [
        BuildingMass(start_dist=30.0, end_dist=50.0, ground_elevation=prof.get_elevation_at(40.0), floors=4, label="Residential"),
        BuildingMass(start_dist=80.0, end_dist=100.0, ground_elevation=prof.get_elevation_at(90.0), floors=4, label="Residential"),
        BuildingMass(start_dist=285.0, end_dist=315.0, ground_elevation=prof.get_elevation_at(300.0), floors=4, label="Commercial"),
        BuildingMass(start_dist=360.0, end_dist=385.0, ground_elevation=prof.get_elevation_at(372.5), floors=3, label="Residential"),
    ]
    prof.buildings = buildings

    veg = [
        VegetationCluster(center_dist=15.0, ground_elevation=prof.get_elevation_at(15.0), width=15.0, tree_count=3),
        VegetationCluster(center_dist=65.0, ground_elevation=prof.get_elevation_at(65.0), width=14.0, tree_count=3),
        VegetationCluster(center_dist=130.0, ground_elevation=prof.get_elevation_at(130.0), width=24.0, tree_count=5),
        VegetationCluster(center_dist=190.0, ground_elevation=prof.get_elevation_at(190.0), width=22.0, tree_count=4),
        VegetationCluster(center_dist=250.0, ground_elevation=prof.get_elevation_at(250.0), width=20.0, tree_count=4),
        VegetationCluster(center_dist=335.0, ground_elevation=prof.get_elevation_at(335.0), width=18.0, tree_count=3),
    ]
    prof.vegetation = veg

    roads = [
        RoadIncision(center_dist=160.0, width=12.0, elevation=prof.get_elevation_at(160.0), name="12 m Planned Street"),
        RoadIncision(center_dist=340.0, width=15.0, elevation=prof.get_elevation_at(340.0), name="15 m District Road"),
    ]
    prof.roads = roads

    if use_lang != "en":
        retranslate_profile_inplace(prof, use_lang)
    return prof
