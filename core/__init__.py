# -*- coding: utf-8 -*-
"""UrbanCrossSection — Core Katmanı (core/__init__.py)."""

from .elements import ElementType, SectionElement, BuildingFacade
from .section_model import CrossSection
from .presets import (
    ALL_PRESETS,
    list_presets,
    get_preset_by_width,
    get_preset_by_id,
    preset_7m_residential,
    preset_10m_local,
    preset_12m_collector,
    preset_15m_collector,
    preset_20m_arterial,
    preset_25m_boulevard,
    preset_30m_transit_boulevard,
    preset_50m_expressway,
    preset_12m_pedestrian_mall,
)
from .svg_exporter import SvgCrossSectionExporter
from .profile_model import (
    BuildingMass,
    VegetationCluster,
    RoadIncision,
    UrbanProfile,
    preset_profile_hillside_aa,
    preset_profile_slope_bb,
)
from .profile_svg import SvgUrbanProfileExporter

__all__ = [
    "ElementType",
    "SectionElement",
    "BuildingFacade",
    "CrossSection",
    "ALL_PRESETS",
    "list_presets",
    "get_preset_by_width",
    "get_preset_by_id",
    "preset_7m_residential",
    "preset_10m_local",
    "preset_12m_collector",
    "preset_15m_collector",
    "preset_20m_arterial",
    "preset_25m_boulevard",
    "preset_30m_transit_boulevard",
    "preset_50m_expressway",
    "preset_12m_pedestrian_mall",
    "SvgCrossSectionExporter",
    "BuildingMass",
    "VegetationCluster",
    "RoadIncision",
    "UrbanProfile",
    "preset_profile_hillside_aa",
    "preset_profile_slope_bb",
    "SvgUrbanProfileExporter",
]
