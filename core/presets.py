# -*- coding: utf-8 -*-
"""UrbanCrossSection — Standard Urban Street Cross-Section Presets (core/presets.py).

Pure Python: Zero qgis or PyQt dependencies.
Defaults to 100% English labels and supports EN / TR switching cleanly.
"""

from .elements import ElementType, SectionElement, BuildingFacade
from .section_model import CrossSection
from .i18n import (
    get_language,
    normalize_lang,
    retranslate_section_inplace,
    PRESET_INFO,
)


def _localize(sec: CrossSection, pid: str, lang=None) -> CrossSection:
    use_lang = normalize_lang(lang or get_language())
    info = PRESET_INFO.get(pid, {}).get(use_lang)
    if info:
        sec.name = info[0]
        sec.description = info[1]
    if use_lang != "en":
        retranslate_section_inplace(sec, use_lang)
    else:
        sec.language = "en"
    return sec


def preset_7m_residential(lang=None):
    """7.00 m — Calmed Residential Street."""
    elements = [
        SectionElement(
            element_type=ElementType.SIDEWALK,
            width=1.50,
            label="Sidewalk (Left)",
            elevation=0.15,
            surface_color="#e2e8f0",
            has_curb=True,
            has_tactile=True,
            pedestrian_count=1,
            description="Residential frontage sidewalk",
        ),
        SectionElement(
            element_type=ElementType.VEHICLE_LANE,
            width=4.00,
            label="Shared Travel Way (30 km/h)",
            elevation=0.0,
            surface_color="#334155",
            vehicle_type="car",
            direction="bidirectional",
            marking="none",
            has_drainage_grate=True,
            description="Traffic-calmed shared local street",
        ),
        SectionElement(
            element_type=ElementType.SIDEWALK,
            width=1.50,
            label="Sidewalk (Right)",
            elevation=0.15,
            surface_color="#e2e8f0",
            has_curb=True,
            has_trees=True,
            has_lighting=True,
            pedestrian_count=1,
            description="Tree-lined residential sidewalk",
        ),
    ]
    sec = CrossSection(
        name="7 m Calmed Residential Street",
        right_of_way=7.0,
        elements=elements,
        left_building=BuildingFacade(side="left", floors=3, setback=2.5, ground_floor_commercial=False, facade_color="#f8fafc", roof_style="sloped_tile"),
        right_building=BuildingFacade(side="right", floors=3, setback=2.5, ground_floor_commercial=False, facade_color="#fef3c7", roof_style="sloped_tile"),
    )
    return _localize(sec, "7m", lang)


def preset_10m_local(lang=None):
    """10.00 m — Neighborhood Distributor Street."""
    elements = [
        SectionElement(
            element_type=ElementType.SIDEWALK,
            width=2.00,
            label="Sidewalk (Left)",
            elevation=0.15,
            surface_color="#e2e8f0",
            has_curb=True,
            has_lighting=True,
            has_tactile=True,
            pedestrian_count=1,
        ),
        SectionElement(
            element_type=ElementType.VEHICLE_LANE,
            width=3.00,
            label="Travel Lane (Inbound)",
            elevation=0.0,
            surface_color="#334155",
            vehicle_type="car",
            direction="forward",
            marking="dashed_white",
        ),
        SectionElement(
            element_type=ElementType.VEHICLE_LANE,
            width=3.00,
            label="Travel Lane (Outbound)",
            elevation=0.0,
            surface_color="#334155",
            vehicle_type="car",
            direction="backward",
            marking="none",
        ),
        SectionElement(
            element_type=ElementType.SIDEWALK,
            width=2.00,
            label="Sidewalk (Right)",
            elevation=0.15,
            surface_color="#e2e8f0",
            has_curb=True,
            has_trees=True,
            has_bench=True,
            pedestrian_count=2,
        ),
    ]
    sec = CrossSection(
        name="10 m Neighborhood Collector",
        right_of_way=10.0,
        elements=elements,
        left_building=BuildingFacade(side="left", floors=4, setback=3.0, ground_floor_commercial=True, shop_name="BAKERY & MARKET"),
        right_building=BuildingFacade(side="right", floors=4, setback=3.0, ground_floor_commercial=False, facade_color="#f1f5f9"),
    )
    return _localize(sec, "10m", lang)


def preset_12m_collector(lang=None):
    """12.00 m — Urban Bike Street."""
    elements = [
        SectionElement(
            element_type=ElementType.SIDEWALK,
            width=2.00,
            label="Sidewalk (Left)",
            elevation=0.15,
            surface_color="#e2e8f0",
            has_curb=True,
            has_lighting=True,
            pedestrian_count=1,
        ),
        SectionElement(
            element_type=ElementType.BIKE_LANE,
            width=1.50,
            label="One-Way Bike Lane",
            elevation=0.05,
            surface_color="#0284c7",
            cyclist_count=1,
            marking="bike_stencil",
        ),
        SectionElement(
            element_type=ElementType.VEHICLE_LANE,
            width=3.25,
            label="Travel Lane (Inbound)",
            elevation=0.0,
            surface_color="#334155",
            vehicle_type="car",
            marking="dashed_white",
        ),
        SectionElement(
            element_type=ElementType.VEHICLE_LANE,
            width=3.25,
            label="Travel Lane (Outbound)",
            elevation=0.0,
            surface_color="#334155",
            vehicle_type="bus",
            marking="none",
        ),
        SectionElement(
            element_type=ElementType.SIDEWALK,
            width=2.00,
            label="Tree-Lined Sidewalk (Right)",
            elevation=0.15,
            surface_color="#e2e8f0",
            has_curb=True,
            has_trees=True,
            has_bike_rack=True,
            pedestrian_count=1,
        ),
    ]
    sec = CrossSection(
        name="12 m Urban Bike Street",
        right_of_way=12.0,
        elements=elements,
        left_building=BuildingFacade(side="left", floors=4, setback=3.0, ground_floor_commercial=True, shop_name="BOOKSHOP & CAFE"),
        right_building=BuildingFacade(side="right", floors=5, setback=3.0, ground_floor_commercial=True, shop_name="PHARMACY"),
    )
    return _localize(sec, "12m", lang)


def preset_15m_collector(lang=None):
    """15.00 m — District Collector Avenue."""
    elements = [
        SectionElement(
            element_type=ElementType.SIDEWALK,
            width=2.50,
            label="Sidewalk (Left)",
            elevation=0.15,
            surface_color="#e2e8f0",
            has_curb=True,
            has_trees=True,
            has_lighting=True,
            has_tactile=True,
            pedestrian_count=2,
        ),
        SectionElement(
            element_type=ElementType.BIKE_LANE,
            width=1.50,
            label="Protected Bike Lane",
            elevation=0.05,
            surface_color="#0284c7",
            cyclist_count=1,
            marking="bike_stencil",
        ),
        SectionElement(
            element_type=ElementType.VEHICLE_LANE,
            width=3.25,
            label="Travel Lane (Inbound)",
            elevation=0.0,
            surface_color="#334155",
            vehicle_type="car",
            marking="dashed_white",
        ),
        SectionElement(
            element_type=ElementType.VEHICLE_LANE,
            width=3.25,
            label="Travel Lane (Outbound)",
            elevation=0.0,
            surface_color="#334155",
            vehicle_type="car",
            marking="solid_white",
        ),
        SectionElement(
            element_type=ElementType.PARKING,
            width=2.00,
            label="Parallel Parking Lane",
            elevation=0.0,
            surface_color="#475569",
            vehicle_type="car",
        ),
        SectionElement(
            element_type=ElementType.SIDEWALK,
            width=2.50,
            label="Wide Sidewalk (Right)",
            elevation=0.15,
            surface_color="#e2e8f0",
            has_curb=True,
            has_trees=True,
            has_bench=True,
            has_bus_shelter=True,
            pedestrian_count=2,
        ),
    ]
    sec = CrossSection(
        name="15 m District Collector Avenue",
        right_of_way=15.0,
        elements=elements,
        left_building=BuildingFacade(side="left", floors=5, setback=3.5, ground_floor_commercial=True, shop_name="CAFE & BISTRO", accent_color="#2563eb"),
        right_building=BuildingFacade(side="right", floors=5, setback=3.5, ground_floor_commercial=True, shop_name="CAFE & BAKERY", accent_color="#dc2626"),
    )
    return _localize(sec, "15m", lang)


def preset_20m_arterial(lang=None):
    """20.00 m — Divided Arterial Boulevard."""
    elements = [
        SectionElement(
            element_type=ElementType.SIDEWALK,
            width=2.50,
            label="Sidewalk (Left)",
            elevation=0.15,
            surface_color="#e2e8f0",
            has_curb=True,
            has_trees=True,
            has_tactile=True,
            pedestrian_count=2,
        ),
        SectionElement(
            element_type=ElementType.BIKE_LANE,
            width=1.50,
            label="Protected Bike Lane",
            elevation=0.05,
            surface_color="#0284c7",
            cyclist_count=1,
            marking="bike_stencil",
        ),
        SectionElement(
            element_type=ElementType.VEHICLE_LANE,
            width=3.00,
            label="Travel Lane 1 (Inbound)",
            elevation=0.0,
            surface_color="#334155",
            vehicle_type="car",
            marking="dashed_white",
        ),
        SectionElement(
            element_type=ElementType.VEHICLE_LANE,
            width=3.00,
            label="Travel Lane 2 (Inbound)",
            elevation=0.0,
            surface_color="#334155",
            vehicle_type="bus",
            marking="none",
        ),
        SectionElement(
            element_type=ElementType.MEDIAN,
            width=1.00,
            label="Green Median",
            elevation=0.20,
            surface_color="#22c55e",
            has_trees=True,
            has_lighting=True,
        ),
        SectionElement(
            element_type=ElementType.VEHICLE_LANE,
            width=3.00,
            label="Travel Lane 1 (Outbound)",
            elevation=0.0,
            surface_color="#334155",
            vehicle_type="car",
            marking="dashed_white",
        ),
        SectionElement(
            element_type=ElementType.VEHICLE_LANE,
            width=3.00,
            label="Travel Lane 2 (Outbound)",
            elevation=0.0,
            surface_color="#334155",
            vehicle_type="car",
            marking="none",
        ),
        SectionElement(
            element_type=ElementType.SIDEWALK,
            width=3.00,
            label="Wide Sidewalk (Right)",
            elevation=0.15,
            surface_color="#e2e8f0",
            has_curb=True,
            has_trees=True,
            has_bench=True,
            pedestrian_count=2,
        ),
    ]
    sec = CrossSection(
        name="20 m Divided Arterial Boulevard",
        right_of_way=20.0,
        elements=elements,
        left_building=BuildingFacade(side="left", floors=6, setback=4.0, ground_floor_commercial=True, shop_name="BANK & OFFICES", accent_color="#0284c7"),
        right_building=BuildingFacade(side="right", floors=6, setback=4.0, ground_floor_commercial=True, shop_name="BISTRO & TERRACE", accent_color="#d97706"),
    )
    return _localize(sec, "20m", lang)


def preset_25m_boulevard(lang=None):
    """25.00 m — Multi-Modal Boulevard."""
    elements = [
        SectionElement(
            element_type=ElementType.SIDEWALK,
            width=3.00,
            label="Promenade Sidewalk (Left)",
            elevation=0.15,
            surface_color="#e2e8f0",
            has_curb=True,
            has_tactile=True,
            pedestrian_count=2,
        ),
        SectionElement(
            element_type=ElementType.LANDSCAPE,
            width=1.50,
            label="Green Verge",
            elevation=0.15,
            surface_color="#86efac",
            has_trees=True,
            has_lighting=True,
            has_bench=True,
        ),
        SectionElement(
            element_type=ElementType.BIKE_LANE,
            width=2.00,
            label="Two-Way Cycle Track",
            elevation=0.05,
            surface_color="#0284c7",
            cyclist_count=1,
            marking="bike_stencil",
        ),
        SectionElement(
            element_type=ElementType.BUFFER,
            width=0.50,
            label="Safety Buffer",
            elevation=0.15,
            surface_color="#94a3b8",
        ),
        SectionElement(
            element_type=ElementType.VEHICLE_LANE,
            width=3.25,
            label="Travel Lane 1 (Inbound)",
            elevation=0.0,
            surface_color="#334155",
            vehicle_type="car",
            marking="dashed_white",
        ),
        SectionElement(
            element_type=ElementType.VEHICLE_LANE,
            width=3.25,
            label="Travel Lane 2 (Inbound)",
            elevation=0.0,
            surface_color="#334155",
            vehicle_type="bus",
            marking="none",
        ),
        SectionElement(
            element_type=ElementType.MEDIAN,
            width=2.00,
            label="Planted Median",
            elevation=0.20,
            surface_color="#22c55e",
            has_trees=True,
            has_lighting=True,
        ),
        SectionElement(
            element_type=ElementType.VEHICLE_LANE,
            width=3.25,
            label="Travel Lane 1 (Outbound)",
            elevation=0.0,
            surface_color="#334155",
            vehicle_type="car",
            marking="dashed_white",
        ),
        SectionElement(
            element_type=ElementType.VEHICLE_LANE,
            width=3.25,
            label="Travel Lane 2 (Outbound)",
            elevation=0.0,
            surface_color="#334155",
            vehicle_type="car",
            marking="none",
        ),
        SectionElement(
            element_type=ElementType.SIDEWALK,
            width=3.00,
            label="Wide Sidewalk (Right)",
            elevation=0.15,
            surface_color="#e2e8f0",
            has_curb=True,
            has_trees=True,
            has_bus_shelter=True,
            pedestrian_count=2,
        ),
    ]
    sec = CrossSection(
        name="25 m Multi-Modal Boulevard",
        right_of_way=25.0,
        elements=elements,
        left_building=BuildingFacade(side="left", floors=7, setback=5.0, ground_floor_commercial=True, shop_name="FASHION & BOUTIQUE"),
        right_building=BuildingFacade(side="right", floors=7, setback=5.0, ground_floor_commercial=True, shop_name="HOTEL & CAFE"),
    )
    return _localize(sec, "25m", lang)


def preset_30m_transit_boulevard(lang=None):
    """30.00 m — Transit Tramway Boulevard."""
    elements = [
        SectionElement(
            element_type=ElementType.SIDEWALK,
            width=3.50,
            label="Promenade Sidewalk (Left)",
            elevation=0.15,
            surface_color="#e2e8f0",
            has_curb=True,
            has_trees=True,
            has_lighting=True,
            pedestrian_count=2,
        ),
        SectionElement(
            element_type=ElementType.BIKE_LANE,
            width=2.00,
            label="Protected Bike Lane",
            elevation=0.05,
            surface_color="#0284c7",
            cyclist_count=1,
            marking="bike_stencil",
        ),
        SectionElement(
            element_type=ElementType.PARKING,
            width=2.00,
            label="Parallel Parking",
            elevation=0.0,
            surface_color="#475569",
            vehicle_type="car",
        ),
        SectionElement(
            element_type=ElementType.VEHICLE_LANE,
            width=3.25,
            label="Travel Lane 1 (Inbound)",
            elevation=0.0,
            surface_color="#334155",
            vehicle_type="car",
            marking="dashed_white",
        ),
        SectionElement(
            element_type=ElementType.VEHICLE_LANE,
            width=3.25,
            label="Travel Lane 2 (Inbound)",
            elevation=0.0,
            surface_color="#334155",
            vehicle_type="car",
            marking="none",
        ),
        SectionElement(
            element_type=ElementType.TRAM_LANE,
            width=6.00,
            label="Dual Grassy Tramway",
            elevation=0.10,
            surface_color="#4ade80",
            description="Dual-track grassy light-rail transit corridor",
        ),
        SectionElement(
            element_type=ElementType.VEHICLE_LANE,
            width=3.25,
            label="Travel Lane 1 (Outbound)",
            elevation=0.0,
            surface_color="#334155",
            vehicle_type="car",
            marking="dashed_white",
        ),
        SectionElement(
            element_type=ElementType.VEHICLE_LANE,
            width=3.25,
            label="Travel Lane 2 (Outbound)",
            elevation=0.0,
            surface_color="#334155",
            vehicle_type="bus",
            marking="none",
        ),
        SectionElement(
            element_type=ElementType.SIDEWALK,
            width=3.50,
            label="Wide Sidewalk (Right)",
            elevation=0.15,
            surface_color="#e2e8f0",
            has_curb=True,
            has_trees=True,
            has_bus_shelter=True,
            has_bench=True,
            pedestrian_count=2,
        ),
    ]
    sec = CrossSection(
        name="30 m Transit Tramway Boulevard",
        right_of_way=30.0,
        elements=elements,
        left_building=BuildingFacade(side="left", floors=8, setback=5.0, ground_floor_commercial=True, shop_name="BUSINESS CENTER"),
        right_building=BuildingFacade(side="right", floors=8, setback=5.0, ground_floor_commercial=True, shop_name="CULTURAL CENTER"),
    )
    return _localize(sec, "30m", lang)


def preset_50m_expressway(lang=None):
    """50.00 m — Express Highway Corridor."""
    elements = [
        SectionElement(element_type=ElementType.SIDEWALK, width=3.00, label="Frontage Sidewalk (Left)", elevation=0.15),
        SectionElement(element_type=ElementType.VEHICLE_LANE, width=6.00, label="Frontage 2 Lanes (Left)", surface_color="#475569", vehicle_type="car"),
        SectionElement(element_type=ElementType.LANDSCAPE, width=3.00, label="Green Buffer (Left)", elevation=0.20, surface_color="#86efac", has_trees=True),
        SectionElement(element_type=ElementType.VEHICLE_LANE, width=10.50, label="Mainline 3 Lanes (Inbound)", surface_color="#1e293b", vehicle_type="car", marking="dashed_white"),
        SectionElement(element_type=ElementType.MEDIAN, width=5.00, label="Wide Median / Barrier", elevation=0.30, surface_color="#22c55e", has_trees=True, has_lighting=True),
        SectionElement(element_type=ElementType.VEHICLE_LANE, width=10.50, label="Mainline 3 Lanes (Outbound)", surface_color="#1e293b", vehicle_type="bus", marking="dashed_white"),
        SectionElement(element_type=ElementType.LANDSCAPE, width=3.00, label="Green Buffer (Right)", elevation=0.20, surface_color="#86efac", has_trees=True),
        SectionElement(element_type=ElementType.VEHICLE_LANE, width=6.00, label="Frontage 2 Lanes (Right)", surface_color="#475569", vehicle_type="car"),
        SectionElement(element_type=ElementType.SIDEWALK, width=3.00, label="Frontage Sidewalk (Right)", elevation=0.15),
    ]
    sec = CrossSection(
        name="50 m Express Highway Corridor",
        right_of_way=50.0,
        elements=elements,
        left_building=BuildingFacade(side="left", floors=5, setback=10.0, ground_floor_commercial=False, facade_color="#e2e8f0"),
        right_building=BuildingFacade(side="right", floors=5, setback=10.0, ground_floor_commercial=False, facade_color="#e2e8f0"),
    )
    return _localize(sec, "50m", lang)


def preset_12m_pedestrian_mall(lang=None):
    """12.00 m — Pedestrian Retail Mall."""
    elements = [
        SectionElement(
            element_type=ElementType.PARKLET,
            width=3.50,
            label="Cafe Terrace (Left)",
            elevation=0.08,
            surface_color="#fed7aa",
            has_curb=False,
            has_bench=True,
            pedestrian_count=2,
            description="Outdoor cafe terrace seating area",
        ),
        SectionElement(
            element_type=ElementType.SIDEWALK,
            width=5.00,
            label="Pedestrian Mall & Emergency Spine",
            elevation=0.05,
            surface_color="#f1f5f9",
            has_trees=True,
            has_lighting=True,
            has_tactile=True,
            pedestrian_count=3,
            cyclist_count=1,
            description="Car-free pedestrian walkway with emergency access clearance",
        ),
        SectionElement(
            element_type=ElementType.PARKLET,
            width=3.50,
            label="Cafe Terrace (Right)",
            elevation=0.08,
            surface_color="#fed7aa",
            has_curb=False,
            has_bench=True,
            has_bike_rack=True,
            pedestrian_count=2,
        ),
    ]
    sec = CrossSection(
        name="12 m Pedestrian Retail Mall",
        right_of_way=12.0,
        elements=elements,
        left_building=BuildingFacade(side="left", floors=4, setback=0.0, ground_floor_commercial=True, shop_name="BISTRO CAFE", accent_color="#b45309"),
        right_building=BuildingFacade(side="right", floors=4, setback=0.0, ground_floor_commercial=True, shop_name="ART GALLERY", accent_color="#047857"),
    )
    return _localize(sec, "12m_pedestrian", lang)


ALL_PRESETS = [
    ("7m", preset_7m_residential),
    ("10m", preset_10m_local),
    ("12m", preset_12m_collector),
    ("12m_pedestrian", preset_12m_pedestrian_mall),
    ("15m", preset_15m_collector),
    ("20m", preset_20m_arterial),
    ("25m", preset_25m_boulevard),
    ("30m", preset_30m_transit_boulevard),
    ("50m", preset_50m_expressway),
]


def list_presets(lang=None):
    """Return metadata for all built-in cross-section templates."""
    result = []
    for pid, fn in ALL_PRESETS:
        sec = fn(lang=lang)
        result.append({
            "id": pid,
            "name": sec.name,
            "right_of_way": sec.right_of_way,
            "description": sec.description,
            "element_count": len(sec.elements),
        })
    return result


def get_preset_by_width(width, lang=None):
    """Return the closest matching street cross-section template for a given width."""
    w = float(width)
    candidates = [fn(lang=lang) for _, fn in ALL_PRESETS]
    best = min(candidates, key=lambda s: abs(s.right_of_way - w))
    res = best.clone()
    res.right_of_way = w
    return res


def get_preset_by_id(preset_id, lang=None):
    """Return a cross-section template by ID."""
    for pid, fn in ALL_PRESETS:
        if pid == preset_id:
            return fn(lang=lang)
    return preset_15m_collector(lang=lang)
