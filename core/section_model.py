# -*- coding: utf-8 -*-
"""UrbanCrossSection — Kesit Modeli (core/section_model.py).

Saf Python: Hiçbir qgis veya PyQt bağımlılığı içermez.
"""

import copy
import json
from .elements import ElementType, SectionElement, BuildingFacade
from .i18n import get_language, normalize_lang, tr_text


class CrossSection:
    """Complete street cross-section engineering and architectural model."""

    def __init__(
        self,
        name=None,
        right_of_way=15.0,
        elements=None,
        left_building=None,
        right_building=None,
        description="",
        show_subgrade=True,
        show_utilities=True,
        has_water_pipe=True,
        has_telecom_pipe=True,
        has_power_cable=True,
        has_gas_pipe=True,
        has_drainage_pipe=True,
        has_sewer_pipe=False,
        has_utility_gallery=False,
        visual_theme="architectural",
        show_buildings=True,
        show_dimensions=True,
        show_cards=True,
        show_slope_arrows=True,
        language=None,
    ):
        self.language = normalize_lang(language or get_language())
        self.name = str(name if name is not None else tr_text("default_section_name", self.language))
        self.right_of_way = max(1.0, float(right_of_way))
        self.elements = list(elements) if elements is not None else []
        self.left_building = left_building or BuildingFacade(side="left", floors=4, setback=3.0)
        self.right_building = right_building or BuildingFacade(side="right", floors=4, setback=3.0)
        self.description = str(description)

        # Yeraltı Altyapı Şebekesi Seçenekleri
        self.show_subgrade = bool(show_subgrade)
        self.show_utilities = bool(show_utilities)
        self.has_water_pipe = bool(has_water_pipe)
        self.has_telecom_pipe = bool(has_telecom_pipe)
        self.has_power_cable = bool(has_power_cable)
        self.has_gas_pipe = bool(has_gas_pipe)
        self.has_drainage_pipe = bool(has_drainage_pipe)
        self.has_sewer_pipe = bool(has_sewer_pipe)
        self.has_utility_gallery = bool(has_utility_gallery)

        # Görsel Sunum & Jüri Seçenekleri
        self.visual_theme = str(visual_theme)
        self.show_buildings = bool(show_buildings)
        self.show_dimensions = bool(show_dimensions)
        self.show_cards = bool(show_cards)
        self.show_slope_arrows = bool(show_slope_arrows)

    @property
    def total_width(self):
        """Tüm kesit elemanlarının toplam genişliği (m)."""
        return round(sum(elem.width for elem in self.elements), 2)

    @property
    def width_difference(self):
        """Yol kırmızı çizgisi (kamulaştırma/ada kenarı) ile elemanlar arasındaki fark (m)."""
        return round(self.right_of_way - self.total_width, 2)

    @property
    def is_balanced(self):
        """Elemanlar toplamı ile yol genişliği birebir örtüşüyor mu?"""
        return abs(self.width_difference) < 0.02

    @property
    def pedestrian_realm_width(self):
        """Yaya ve yeşil alan genişliği toplamı (kaldırım + ağaç/peyzaj)."""
        return round(
            sum(
                e.width
                for e in self.elements
                if e.element_type in (ElementType.SIDEWALK, ElementType.LANDSCAPE)
            ),
            2,
        )

    @property
    def vehicular_realm_width(self):
        """Taşıt ve otopark alanı genişliği toplamı (taşıt şeritleri, park, refüj)."""
        return round(
            sum(
                e.width
                for e in self.elements
                if e.element_type
                in (ElementType.VEHICLE_LANE, ElementType.PARKING, ElementType.MEDIAN, ElementType.TRAM_LANE)
            ),
            2,
        )

    @property
    def cycling_realm_width(self):
        """Bisiklet ve mikromobilite alanı genişliği toplamı."""
        return round(
            sum(
                e.width
                for e in self.elements
                if e.element_type in (ElementType.BIKE_LANE, ElementType.BUFFER)
            ),
            2,
        )

    def add_element(self, element, index=None):
        """Yeni bir kesit elemanı ekler."""
        if index is None or index >= len(self.elements):
            self.elements.append(element)
        else:
            self.elements.insert(max(0, int(index)), element)

    def remove_element(self, index):
        """Belirtilen indeksteki elemanı siler."""
        if 0 <= index < len(self.elements):
            return self.elements.pop(index)
        return None

    def move_element(self, from_idx, to_idx):
        """Elemanın kesitteki sırasını değiştirir (sola/sağa kaydırır)."""
        if 0 <= from_idx < len(self.elements) and 0 <= to_idx < len(self.elements):
            item = self.elements.pop(from_idx)
            self.elements.insert(to_idx, item)
            return True
        return False

    def update_element(self, index, **kwargs):
        """Mevcut bir elemanın özelliklerini günceller."""
        if 0 <= index < len(self.elements):
            elem = self.elements[index]
            for k, v in kwargs.items():
                if hasattr(elem, k):
                    setattr(elem, k, v)
            return True
        return False

    def validate(self):
        """MPYY ve Karayolları tasarım standartlarına göre teknik denetim yapar."""
        warnings = []
        errors = []

        # 1. Toplam genişlik denetimi
        diff = self.width_difference
        if abs(diff) >= 0.05:
            if diff > 0:
                warnings.append(
                    f"Toplam eleman genişliği ({self.total_width:.2f} m), yol sınırından ({self.right_of_way:.2f} m) "
                    f"{abs(diff):.2f} m daha DAR. Kalan alan boşluk olarak kalacaktır."
                )
            else:
                errors.append(
                    f"Toplam eleman genişliği ({self.total_width:.2f} m), yol sınırını ({self.right_of_way:.2f} m) "
                    f"{abs(diff):.2f} m AŞIYOR!"
                )

        # 2. Asgari kaldırım genişliği denetimi (MPYY: en az 1.50 m)
        sidewalks = [e for e in self.elements if e.element_type == ElementType.SIDEWALK]
        if not sidewalks:
            warnings.append("Kesitte hiç yaya kaldırımı bulunmuyor!")
        else:
            for i, sw in enumerate(sidewalks):
                if sw.width < 1.50:
                    warnings.append(
                        f"Kaldırım #{i+1} ({sw.width:.2f} m) MPYY asgari standardı olan 1.50 m'nin altında!"
                    )

        # 3. Asgari taşıt şeridi genişliği denetimi (Karayolları / MPYY: en az 2.75 m)
        lanes = [e for e in self.elements if e.element_type == ElementType.VEHICLE_LANE]
        for i, lane in enumerate(lanes):
            if lane.width < 2.75:
                warnings.append(
                    f"Taşıt şeridi #{i+1} ({lane.width:.2f} m) asgari 2.75 m standardının altında!"
                )

        # 4. Bisiklet yolu denetimi (en az 1.20 m)
        bikes = [e for e in self.elements if e.element_type == ElementType.BIKE_LANE]
        for i, bike in enumerate(bikes):
            if bike.width < 1.20:
                warnings.append(
                    f"Bisiklet yolu #{i+1} ({bike.width:.2f} m) güvenli asgari 1.20 m genişliğin altında!"
                )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    def summary_stats(self):
        """Oransal ve boyutsal özet istatistikler."""
        tot = max(0.01, self.total_width)
        return {
            "name": self.name,
            "right_of_way_m": self.right_of_way,
            "total_width_m": self.total_width,
            "difference_m": self.width_difference,
            "is_balanced": self.is_balanced,
            "pedestrian_m": self.pedestrian_realm_width,
            "pedestrian_pct": round((self.pedestrian_realm_width / tot) * 100, 1),
            "vehicular_m": self.vehicular_realm_width,
            "vehicular_pct": round((self.vehicular_realm_width / tot) * 100, 1),
            "cycling_m": self.cycling_realm_width,
            "cycling_pct": round((self.cycling_realm_width / tot) * 100, 1),
            "element_count": len(self.elements),
            "left_building_floors": self.left_building.floors,
            "right_building_floors": self.right_building.floors,
        }

    def toggle_utility(self, key):
        """Belirtilen altyapı hattını açar/kapatır ve yeni durumunu döndürür."""
        mapping = {
            "water": "has_water_pipe",
            "telecom": "has_telecom_pipe",
            "power": "has_power_cable",
            "gas": "has_gas_pipe",
            "drainage": "has_drainage_pipe",
            "sewer": "has_sewer_pipe",
            "gallery": "has_utility_gallery",
        }
        attr = mapping.get(key)
        if attr and hasattr(self, attr):
            new_val = not getattr(self, attr)
            setattr(self, attr, new_val)
            return new_val
        return False

    def to_dict(self):
        return {
            "name": self.name,
            "right_of_way": round(self.right_of_way, 2),
            "elements": [e.to_dict() for e in self.elements],
            "left_building": self.left_building.to_dict(),
            "right_building": self.right_building.to_dict(),
            "description": self.description,
            "show_subgrade": self.show_subgrade,
            "show_utilities": self.show_utilities,
            "has_water_pipe": self.has_water_pipe,
            "has_telecom_pipe": self.has_telecom_pipe,
            "has_power_cable": self.has_power_cable,
            "has_gas_pipe": self.has_gas_pipe,
            "has_drainage_pipe": self.has_drainage_pipe,
            "has_sewer_pipe": self.has_sewer_pipe,
            "has_utility_gallery": self.has_utility_gallery,
            "visual_theme": self.visual_theme,
            "show_buildings": self.show_buildings,
            "show_dimensions": self.show_dimensions,
            "show_cards": self.show_cards,
            "show_slope_arrows": self.show_slope_arrows,
            "language": getattr(self, "language", "en"),
        }

    @classmethod
    def from_dict(cls, data):
        elements = [SectionElement.from_dict(ed) for ed in data.get("elements", [])]
        left_b = BuildingFacade.from_dict(data["left_building"]) if "left_building" in data else None
        right_b = BuildingFacade.from_dict(data["right_building"]) if "right_building" in data else None
        lang = data.get("language")
        return cls(
            name=data.get("name", tr_text("default_section_name", lang)),
            right_of_way=data.get("right_of_way", 15.0),
            elements=elements,
            left_building=left_b,
            right_building=right_b,
            description=data.get("description", ""),
            show_subgrade=data.get("show_subgrade", True),
            show_utilities=data.get("show_utilities", True),
            has_water_pipe=data.get("has_water_pipe", True),
            has_telecom_pipe=data.get("has_telecom_pipe", True),
            has_power_cable=data.get("has_power_cable", True),
            has_gas_pipe=data.get("has_gas_pipe", True),
            has_drainage_pipe=data.get("has_drainage_pipe", True),
            has_sewer_pipe=data.get("has_sewer_pipe", False),
            has_utility_gallery=data.get("has_utility_gallery", False),
            visual_theme=data.get("visual_theme", "architectural"),
            show_buildings=data.get("show_buildings", True),
            show_dimensions=data.get("show_dimensions", True),
            show_cards=data.get("show_cards", True),
            show_slope_arrows=data.get("show_slope_arrows", True),
            language=lang,
        )

    def to_json(self, indent=2):
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_json(cls, json_str):
        return cls.from_dict(json.loads(json_str))

    def clone(self):
        return copy.deepcopy(self)
