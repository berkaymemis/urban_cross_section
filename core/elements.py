# -*- coding: utf-8 -*-
"""UrbanCrossSection — Gelişmiş Kesit Elemanları ve Tip Tanımları (core/elements.py).

Saf Python: Hiçbir qgis veya PyQt bağımlılığı içermez.
"""

import copy
from .i18n import element_default_label, get_language, normalize_lang


class ElementType:
    SIDEWALK = "sidewalk"           # Yaya kaldırımı
    LANDSCAPE = "landscape"         # Ağaçlandırma / yeşil şerit
    BIKE_LANE = "bike_lane"         # Bisiklet yolu
    PARKING = "parking"             # Otopark şeridi (paralel / verev)
    VEHICLE_LANE = "vehicle_lane"   # Taşıt şeridi (genel / otobüs)
    BUS_LANE = "bus_lane"           # Ayrılmış otobüs şeridi
    MEDIAN = "median"               # Orta refüj / ayırıcı
    TRAM_LANE = "tram_lane"         # Raylı sistem / tramvay
    BUFFER = "buffer"               # Güvenlik / ayırıcı bordür bandı
    PARKLET = "parklet"             # Kafe terası / cep parklet


class SectionElement:
    """Tekil bir yol kesiti elemanı (kaldırım, şerit, refüj, vb.)."""

    def __init__(
        self,
        element_type=ElementType.VEHICLE_LANE,
        width=3.0,
        label="",
        elevation=0.0,
        surface_color="#374151",
        has_trees=False,
        tree_type="plane_tree",     # "plane_tree" (çınar), "linden" (ıhlamur), "pine" (çam), "columnar"
        has_lighting=False,
        lighting_style="modern_led", # "modern_led", "classic_heritage", "catenary"
        has_tactile=False,          # Görme engelli sarı takip bandı
        has_curb=True,              # Pahlı granit bordür
        has_bench=False,            # Oturma bankı
        has_bike_rack=False,        # Bisiklet park demiri
        has_bus_shelter=False,      # Cam otobüs bekleme durağı
        has_drainage_grate=False,   # Yağmur suyu drenaj ızgarası
        vehicle_type=None,          # "car", "suv", "bus", "van", "scooter", None
        direction="forward",        # "forward", "backward", "bidirectional"
        marking="dashed_white",     # "none", "dashed_white", "solid_white", "double_yellow", "bike_stencil", "zebra"
        pavement_pattern="stone",   # "stone", "asphalt", "red_brick", "blue_thermoplastic", "green_grass", "gravel"
        slope_pct=-2.0,             # Yüzde enine eğim (-2.0 = dışa doğru %2 drenaj)
        pedestrian_count=0,         # 0..4 arası yaya
        cyclist_count=0,            # 0..2 arası bisikletli
        description="",
    ):
        self.element_type = element_type
        self.width = max(0.2, float(width))
        self.label = label or self._default_label(element_type)
        self.elevation = float(elevation)
        self.surface_color = surface_color or self._default_color(element_type)
        self.has_trees = bool(has_trees)
        self.tree_type = tree_type
        self.has_lighting = bool(has_lighting)
        self.lighting_style = lighting_style
        self.has_tactile = bool(has_tactile)
        self.has_curb = bool(has_curb)
        self.has_bench = bool(has_bench)
        self.has_bike_rack = bool(has_bike_rack)
        self.has_bus_shelter = bool(has_bus_shelter)
        self.has_drainage_grate = bool(has_drainage_grate)
        self.vehicle_type = vehicle_type
        self.direction = direction
        self.marking = marking
        self.pavement_pattern = pavement_pattern
        self.slope_pct = float(slope_pct)
        self.pedestrian_count = int(pedestrian_count)
        self.cyclist_count = int(cyclist_count)
        self.description = description

    @staticmethod
    def _default_label(elem_type, lang=None):
        return element_default_label(elem_type, lang or get_language())

    @staticmethod
    def _default_color(elem_type):
        colors = {
            ElementType.SIDEWALK: "#e2e8f0",       # Açık gri granit plak taş
            ElementType.LANDSCAPE: "#86efac",      # Açık zümrüt yeşili çim/toprak
            ElementType.BIKE_LANE: "#0284c7",      # Canlı İzmir mavisi bisiklet yolu
            ElementType.PARKING: "#475569",        # Koyu gri park asfaltı
            ElementType.VEHICLE_LANE: "#334155",   # Standart kaliteli aşınma asfaltı
            ElementType.BUS_LANE: "#b91c1c",       # Kırmızı boyalı otobüs şeridi
            ElementType.MEDIAN: "#22c55e",         # Orta refüj peyzajı
            ElementType.TRAM_LANE: "#4ade80",      # Çimli yeşil tramvay hattı
            ElementType.BUFFER: "#94a3b8",         # Bordür / delinatör bandı
            ElementType.PARKLET: "#fed7aa",        # Ahşap kompozit deck
        }
        return colors.get(elem_type, "#9ca3af")

    def to_dict(self):
        return {
            "element_type": self.element_type,
            "width": round(self.width, 2),
            "label": self.label,
            "elevation": round(self.elevation, 2),
            "surface_color": self.surface_color,
            "has_trees": self.has_trees,
            "tree_type": self.tree_type,
            "has_lighting": self.has_lighting,
            "lighting_style": self.lighting_style,
            "has_tactile": self.has_tactile,
            "has_curb": self.has_curb,
            "has_bench": self.has_bench,
            "has_bike_rack": self.has_bike_rack,
            "has_bus_shelter": self.has_bus_shelter,
            "has_drainage_grate": self.has_drainage_grate,
            "vehicle_type": self.vehicle_type,
            "direction": self.direction,
            "marking": self.marking,
            "pavement_pattern": self.pavement_pattern,
            "slope_pct": round(self.slope_pct, 1),
            "pedestrian_count": self.pedestrian_count,
            "cyclist_count": self.cyclist_count,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)

    def clone(self):
        return copy.deepcopy(self)


class BuildingFacade:
    """Kesitin sağ veya solundaki mimari bina gabarisi ve kentsel cephesi."""

    def __init__(
        self,
        side="left",                 # "left" or "right"
        floors=4,                    # Floor count (1..25)
        floor_height=3.0,            # Floor height (meters)
        setback=3.0,                 # Front setback distance (meters)
        ground_floor_commercial=True, # Ground floor retail storefront
        shop_name=None,              # Storefront sign text
        roof_style="parapet_cornice", # "parapet_cornice", "sloped_tile", "flat"
        has_balconies=True,          # French balconies
        facade_style="modern_brick", # "modern_brick", "warm_stone", "plaster_white", "glass_curtain"
        facade_color="#f1f5f9",      # Main facade color
        accent_color="#2563eb",      # Awning / accent color
    ):
        self.side = side
        self.floors = max(1, min(25, int(floors)))
        self.floor_height = max(2.5, min(5.0, float(floor_height)))
        self.setback = max(0.0, float(setback))
        self.ground_floor_commercial = bool(ground_floor_commercial)
        is_tr = (normalize_lang(get_language()) == "tr")
        default_left = "KAFE & KİTABEVİ" if is_tr else "CAFE & BOOKS"
        default_right = "ECZANE & PASTANE" if is_tr else "PHARMACY & BAKERY"
        self.shop_name = shop_name if shop_name else (default_left if side == "left" else default_right)
        self.roof_style = roof_style
        self.has_balconies = bool(has_balconies)
        self.facade_style = facade_style
        self.facade_color = facade_color
        self.accent_color = accent_color

    @property
    def total_height(self):
        """Toplam bina saçak kotu yüksekliği (metre)."""
        return round(self.floors * self.floor_height, 2)

    def to_dict(self):
        return {
            "side": self.side,
            "floors": self.floors,
            "floor_height": round(self.floor_height, 2),
            "setback": round(self.setback, 2),
            "ground_floor_commercial": self.ground_floor_commercial,
            "shop_name": self.shop_name,
            "roof_style": self.roof_style,
            "has_balconies": self.has_balconies,
            "facade_style": self.facade_style,
            "facade_color": self.facade_color,
            "accent_color": self.accent_color,
            "total_height": self.total_height,
        }

    @classmethod
    def from_dict(cls, data):
        clean_data = {k: v for k, v in data.items() if k != "total_height"}
        return cls(**clean_data)

    def clone(self):
        return copy.deepcopy(self)
