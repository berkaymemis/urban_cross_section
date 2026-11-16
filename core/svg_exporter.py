# -*- coding: utf-8 -*-
"""UrbanCrossSection — Gelişmiş Mimari Vektörel SVG Çizim ve İhracat Motoru (core/svg_exporter.py).

Saf Python: Hiçbir qgis veya PyQt bağımlılığı içermez.
Standart SVG 1.1 uyumlu, ölçekli, mimari yarışma ve jüri paftası kalitesinde vektör çıktı üretir.
"""

import math
from xml.sax.saxutils import escape
from .elements import ElementType
from .i18n import get_language, tr_text


class SvgCrossSectionExporter:
    """CrossSection modelinden jüri ve yarışma kalitesinde mimari vektörel SVG üretir."""

    def __init__(self, section, pixels_per_meter=32.0, margin_x=140, margin_top=150, margin_bottom=160):
        self.sec = section
        self.ppm = float(pixels_per_meter)
        self.margin_x = float(margin_x)
        self.margin_top = float(margin_top)
        self.margin_bottom = float(margin_bottom)

        self.left_bldg = self.sec.left_building
        self.right_bldg = self.sec.right_building

        self.left_setback_px = self.left_bldg.setback * self.ppm
        self.right_setback_px = self.right_bldg.setback * self.ppm
        self.road_width_px = self.sec.total_width * self.ppm

        # Binalar için genişlik
        self.bldg_width_px = 7.5 * self.ppm

        self.canvas_width = int(
            self.margin_x * 2
            + self.bldg_width_px * 2
            + self.left_setback_px
            + self.road_width_px
            + self.right_setback_px
        )

        max_bldg_h = max(self.left_bldg.total_height, self.right_bldg.total_height, 12.0)
        self.canvas_height = int(self.margin_top + max_bldg_h * self.ppm + self.margin_bottom)

        self.y_ground = self.canvas_height - self.margin_bottom
        self.x_road_start = self.margin_x + self.bldg_width_px + self.left_setback_px

    def export_svg(self):
        """SVG içeriğini string olarak üretir."""
        svg_parts = []
        svg_parts.append(
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.canvas_width} {self.canvas_height}" '
            f'width="{self.canvas_width}" height="{self.canvas_height}">'
        )
        svg_parts.append(self._render_defs())
        svg_parts.append(self._render_background())
        if getattr(self.sec, "show_buildings", True):
            svg_parts.append(self._render_buildings())
        svg_parts.append(self._render_road_elements())
        svg_parts.append(self._render_furniture_and_trees())
        svg_parts.append(self._render_scale_figures())
        if getattr(self.sec, "show_dimensions", True):
            svg_parts.append(self._render_dimensions())
        svg_parts.append(self._render_title_block())
        svg_parts.append('</svg>')
        return "\n".join(svg_parts)

    def save_to_file(self, filepath):
        """SVG dosyasını diske kaydeder."""
        content = self.export_svg()
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return filepath

    # -------------------------------------------------------------------------
    # SVG Alt Parçaları
    # -------------------------------------------------------------------------

    def _render_defs(self):
        return """
  <defs>
    <!-- Soft Sky Gradient -->
    <linearGradient id="skyGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#f8fafc" stop-opacity="1"/>
      <stop offset="70%" stop-color="#f1f5f9" stop-opacity="1"/>
      <stop offset="100%" stop-color="#e2e8f0" stop-opacity="1"/>
    </linearGradient>

    <!-- Asphalt Texture -->
    <pattern id="asphaltPat" width="16" height="16" patternUnits="userSpaceOnUse">
      <rect width="16" height="16" fill="#334155"/>
      <circle cx="4" cy="4" r="0.75" fill="#475569"/>
      <circle cx="12" cy="12" r="0.75" fill="#475569"/>
      <circle cx="12" cy="4" r="0.5" fill="#1e293b"/>
      <circle cx="4" cy="12" r="0.5" fill="#1e293b"/>
    </pattern>

    <!-- Granite Paver Texture -->
    <pattern id="granitePaver" width="20" height="10" patternUnits="userSpaceOnUse">
      <rect width="20" height="10" fill="#f1f5f9" stroke="#cbd5e1" stroke-width="0.6"/>
      <line x1="10" y1="0" x2="10" y2="10" stroke="#cbd5e1" stroke-width="0.6"/>
    </pattern>

    <!-- Earth / Subgrade Hatch -->
    <pattern id="earthHatch" width="12" height="12" patternTransform="rotate(45 0 0)" patternUnits="userSpaceOnUse">
      <rect width="12" height="12" fill="#e7e5e4"/>
      <line x1="0" y1="0" x2="0" y2="12" stroke="#a8a29e" stroke-width="0.8"/>
    </pattern>

    <!-- Botanical Canopy Gradient -->
    <radialGradient id="treeCanopy1" cx="40%" cy="35%" r="65%">
      <stop offset="0%" stop-color="#4ade80"/>
      <stop offset="70%" stop-color="#16a34a"/>
      <stop offset="100%" stop-color="#14532d"/>
    </radialGradient>

    <!-- Light Cone Gradient -->
    <linearGradient id="lightConeGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#fef08a" stop-opacity="0.35"/>
      <stop offset="100%" stop-color="#fef08a" stop-opacity="0.0"/>
    </linearGradient>

    <!-- Median Grass Gradient -->
    <linearGradient id="grassGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#4ade80"/>
      <stop offset="100%" stop-color="#22c55e"/>
    </linearGradient>
  </defs>"""

    def _render_background(self):
        return f'  <rect width="{self.canvas_width}" height="{self.canvas_height}" fill="url(#skyGrad)"/>'

    def _render_buildings(self):
        parts = []
        # Left Building
        left_h_px = self.left_bldg.total_height * self.ppm
        left_x = self.margin_x
        left_y = self.y_ground - left_h_px
        parts.append(f'  <!-- Left Building: {self.left_bldg.floors}F / {self.left_bldg.total_height:.1f}m -->')
        parts.extend(self._render_single_building(left_x, left_y, self.bldg_width_px, left_h_px, self.left_bldg))

        # Right Building
        right_h_px = self.right_bldg.total_height * self.ppm
        right_x = self.x_road_start + self.road_width_px + self.right_setback_px
        right_y = self.y_ground - right_h_px
        parts.append(f'  <!-- Right Building: {self.right_bldg.floors}F / {self.right_bldg.total_height:.1f}m -->')
        parts.extend(self._render_single_building(right_x, right_y, self.bldg_width_px, right_h_px, self.right_bldg))

        # Ön bahçeler (varsa)
        if self.left_bldg.setback > 0.05:
            sb_x = left_x + self.bldg_width_px
            parts.append(
                f'  <rect x="{sb_x}" y="{self.y_ground - 6}" width="{self.left_setback_px}" height="6" '
                f'fill="url(#grassGrad)" stroke="#16a34a" stroke-width="0.8"/>'
            )
            # Ön bahçe bordür
            parts.append(
                f'  <line x1="{sb_x}" y1="{self.y_ground - 6}" x2="{sb_x + self.left_setback_px}" y2="{self.y_ground - 6}" '
                f'stroke="#0f766e" stroke-width="1.2"/>'
            )

        if self.right_bldg.setback > 0.05:
            sb_x = self.x_road_start + self.road_width_px
            parts.append(
                f'  <rect x="{sb_x}" y="{self.y_ground - 6}" width="{self.right_setback_px}" height="6" '
                f'fill="url(#grassGrad)" stroke="#16a34a" stroke-width="0.8"/>'
            )
            parts.append(
                f'  <line x1="{sb_x}" y1="{self.y_ground - 6}" x2="{sb_x + self.right_setback_px}" y2="{self.y_ground - 6}" '
                f'stroke="#0f766e" stroke-width="1.2"/>'
            )

        return "\n".join(parts)

    def _render_single_building(self, bx, by, bw, bh, bldg):
        res = []
        # 1. Ana Cephe Gövdesi
        res.append(
            f'  <rect x="{bx}" y="{by}" width="{bw}" height="{bh}" '
            f'fill="{bldg.facade_color}" stroke="#475569" stroke-width="1.8"/>'
        )

        # 2. Çatı / Parapet
        if bldg.roof_style == "sloped_tile":
            # Eğimli kiremit çatı
            roof_h = 2.2 * self.ppm
            res.append(
                f'  <polygon points="{bx - 6},{by} {bx + bw / 2},{by - roof_h} {bx + bw + 6},{by}" '
                f'fill="#b45309" stroke="#78350f" stroke-width="1.5"/>'
            )
            # Kiremit derz çizgileri
            res.append(
                f'  <line x1="{bx}" y1="{by}" x2="{bx + bw}" y2="{by}" stroke="#78350f" stroke-width="2"/>'
            )
        else:
            # Modern saçak silmesi / korniş (Cornice)
            res.append(
                f'  <rect x="{bx - 4}" y="{by - 7}" width="{bw + 8}" height="7" '
                f'fill="#334155" stroke="#1e293b" stroke-width="1.2"/>'
            )
            res.append(
                f'  <rect x="{bx - 2}" y="{by - 12}" width="{bw + 4}" height="5" '
                f'fill="#64748b" stroke="#334155" stroke-width="1"/>'
            )

        # Elevation Datum Tag
        level_x = bx + bw + 8 if bldg.side == "left" else bx - 8
        anchor = "start" if bldg.side == "left" else "end"
        lang = getattr(self.sec, "language", get_language())
        fl_suffix = tr_text("svg_floor_suffix", lang)
        res.append(
            f'  <text x="{level_x}" y="{by + 4}" font-family="sans-serif" font-size="9" font-weight="bold" '
            f'fill="#475569" text-anchor="{anchor}">▼ +{bldg.total_height:.1f}m ({bldg.floors}{fl_suffix})</text>'
        )

        # 3. Kat Pencereleri ve Zemin Kat
        floor_h = bldg.floor_height * self.ppm
        for f in range(bldg.floors):
            fy = by + bh - (f + 1) * floor_h

            if f == 0 and bldg.ground_floor_commercial:
                # --- ZEMİN KAT TİCARET / VİTRİN ---
                # Büyük vitrin camı
                res.append(
                    f'  <rect x="{bx + 8}" y="{fy + 10}" width="{bw - 16}" height="{floor_h - 14}" '
                    f'fill="#e0f2fe" stroke="#0284c7" stroke-width="1.2"/>'
                )
                # Dükkan Kapısı
                door_w = 26
                res.append(
                    f'  <rect x="{bx + 16}" y="{fy + 14}" width="{door_w}" height="{floor_h - 18}" '
                    f'fill="#bae6fd" stroke="#0369a1" stroke-width="1"/>'
                )
                res.append(
                    f'  <line x1="{bx + 16 + door_w / 2}" y1="{fy + 14}" x2="{bx + 16 + door_w / 2}" y2="{fy + floor_h - 4}" '
                    f'stroke="#0369a1" stroke-width="0.8"/>'
                )

                # Şık Çizgili Tente (Awning)
                awning_y = fy + 4
                res.append(
                    f'  <polygon points="{bx + 4},{awning_y} {bx + bw - 4},{awning_y} {bx + bw - 10},{awning_y + 18} {bx + 10},{awning_y + 18}" '
                    f'fill="{bldg.accent_color}" stroke="#1e3a8a" stroke-width="1.2"/>'
                )
                # Tente çizgileri
                for tx in range(int(bx + 12), int(bx + bw - 12), 16):
                    res.append(f'  <line x1="{tx}" y1="{awning_y}" x2="{tx}" y2="{awning_y + 18}" stroke="#ffffff" stroke-width="2.5"/>')

                # Dükkan Tabelası
                res.append(
                    f'  <rect x="{bx + 12}" y="{fy - 8}" width="{bw - 24}" height="11" rx="2" fill="#1e293b"/>'
                )
                res.append(
                    f'  <text x="{bx + bw / 2}" y="{fy}" font-family="sans-serif" font-size="7.5" font-weight="bold" '
                    f'fill="#f8fafc" text-anchor="middle">{escape(bldg.shop_name)}</text>'
                )

            else:
                # --- NORMAL KATLAR / PENCERELER ---
                num_win = max(2, int(bw / (1.6 * self.ppm)))
                win_w = 22
                win_h = 32
                gap = (bw - num_win * win_w) / (num_win + 1)

                for w_idx in range(num_win):
                    wx = bx + gap + w_idx * (win_w + gap)
                    wy = fy + (floor_h - win_h) / 2 + 4

                    # Pencere Sövesi / Çerçevesi
                    res.append(
                        f'  <rect x="{wx - 1.5}" y="{wy - 1.5}" width="{win_w + 3}" height="{win_h + 3}" '
                        f'fill="#ffffff" stroke="#94a3b8" stroke-width="0.8"/>'
                    )
                    # Cam
                    res.append(
                        f'  <rect x="{wx}" y="{wy}" width="{win_w}" height="{win_h}" '
                        f'fill="#e2e8f0" stroke="#64748b" stroke-width="1"/>'
                    )
                    # Bölüntü (Muntin)
                    res.append(f'  <line x1="{wx + win_w / 2}" y1="{wy}" x2="{wx + win_w / 2}" y2="{wy + win_h}" stroke="#94a3b8" stroke-width="0.8"/>')
                    res.append(f'  <line x1="{wx}" y1="{wy + win_h * 0.35}" x2="{wx + win_w}" y2="{wy + win_h * 0.35}" stroke="#94a3b8" stroke-width="0.8"/>')

                    # Fransız Balkon Korkuluğu (varsa)
                    if bldg.has_balconies and w_idx == 0:
                        res.append(
                            f'  <rect x="{wx - 2}" y="{wy + win_h - 10}" width="{win_w + 4}" height="10" '
                            f'fill="none" stroke="#334155" stroke-width="1.2"/>'
                        )
                        for rx in range(int(wx), int(wx + win_w), 4):
                            res.append(f'  <line x1="{rx}" y1="{wy + win_h - 10}" x2="{rx}" y2="{wy + win_h}" stroke="#334155" stroke-width="0.8"/>')

        return res

    def _render_road_elements(self):
        parts = ['  <!-- Street Elements, Layers & Pavements -->']
        cur_x = self.x_road_start

        for elem in self.sec.elements:
            ew_px = elem.width * self.ppm
            eh_px = max(0.0, elem.elevation * self.ppm)
            ey = self.y_ground - eh_px

            # Yüzey Kaplaması Seçimi
            if elem.element_type == ElementType.SIDEWALK:
                fill = "url(#granitePaver)"
            elif elem.element_type in (ElementType.VEHICLE_LANE, ElementType.PARKING):
                fill = "url(#asphaltPat)"
            elif elem.element_type in (ElementType.LANDSCAPE, ElementType.MEDIAN):
                fill = "url(#grassGrad)"
            else:
                fill = elem.surface_color

            # 1. Aşınma / Yüzey Tabakası
            parts.append(
                f'  <rect x="{cur_x}" y="{ey}" width="{ew_px}" height="{14 + eh_px}" '
                f'fill="{fill}" stroke="#334155" stroke-width="1"/>'
            )

            # 2. Temel ve Altyapı Taraması (Mekanik Temel Dolgusu)
            if getattr(self.sec, "show_subgrade", True):
                parts.append(
                    f'  <rect x="{cur_x}" y="{self.y_ground + 14}" width="{ew_px}" height="28" '
                    f'fill="url(#earthHatch)" stroke="#78716c" stroke-width="0.6"/>'
                )

            # 3. Granit Pahlı Bordür
            if elem.has_curb:
                curb_w = 6
                curb_h = eh_px + 6
                parts.append(
                    f'  <rect x="{cur_x + ew_px - curb_w}" y="{self.y_ground - eh_px}" width="{curb_w}" height="{curb_h}" '
                    f'fill="#94a3b8" stroke="#475569" stroke-width="0.8"/>'
                )

            # 4. Sarı Görme Engelli Takip Bandı (Tactile Paving)
            if elem.has_tactile:
                parts.append(
                    f'  <rect x="{cur_x + 12}" y="{ey + 1}" width="14" height="3" fill="#facc15" stroke="#eab308" stroke-width="0.5"/>'
                )

            # 5. Bisiklet Şablonu (Bike Stencil)
            if elem.element_type == ElementType.BIKE_LANE:
                bx = cur_x + ew_px / 2
                by = ey + 7
                parts.append(f'  <circle cx="{bx - 8}" cy="{by}" r="4" fill="none" stroke="#ffffff" stroke-width="1.4"/>')
                parts.append(f'  <circle cx="{bx + 8}" cy="{by}" r="4" fill="none" stroke="#ffffff" stroke-width="1.4"/>')
                parts.append(f'  <line x1="{bx - 8}" y1="{by}" x2="{bx}" y2="{by - 5}" stroke="#ffffff" stroke-width="1.4"/>')
                parts.append(f'  <line x1="{bx}" y1="{by - 5}" x2="{bx + 8}" y2="{by}" stroke="#ffffff" stroke-width="1.4"/>')

            # 6. Şerit İşaretleri
            if elem.marking == "dashed_white":
                parts.append(
                    f'  <line x1="{cur_x + ew_px}" y1="{self.y_ground - 1}" x2="{cur_x + ew_px}" y2="{self.y_ground + 1}" '
                    f'stroke="#ffffff" stroke-width="3" stroke-dasharray="10,6"/>'
                )
            elif elem.marking == "solid_white":
                parts.append(
                    f'  <line x1="{cur_x + ew_px}" y1="{self.y_ground - 1}" x2="{cur_x + ew_px}" y2="{self.y_ground + 1}" '
                    f'stroke="#ffffff" stroke-width="3"/>'
                )

            # 7. Tramvay Rayları
            if elem.element_type == ElementType.TRAM_LANE:
                r_mid = cur_x + ew_px / 2
                for roff in (-22, -10, 10, 22):
                    parts.append(
                        f'  <rect x="{r_mid + roff}" y="{ey - 3}" width="4" height="5" fill="#64748b" stroke="#0f172a" stroke-width="0.8"/>'
                    )

            cur_x += ew_px

        # Zemin alt çizgisi
        sub_y = (self.y_ground + 42) if getattr(self.sec, "show_subgrade", True) else (self.y_ground + 14)
        parts.append(
            f'  <line x1="{self.margin_x - 10}" y1="{sub_y}" '
            f'x2="{self.canvas_width - self.margin_x + 10}" y2="{sub_y}" stroke="#334155" stroke-width="2"/>'
        )

        # 8. Yeraltı Altyapı Boru Şebekesi (SVG İhracatı)
        if getattr(self.sec, "show_subgrade", True) and getattr(self.sec, "show_utilities", True):
            pipe_y = self.y_ground + 28
            if getattr(self.sec, "has_utility_gallery", False):
                gx = self.x_road_start + 18
                parts.append(f'  <rect x="{gx}" y="{self.y_ground + 17}" width="62" height="22" fill="#1e293b" stroke="#cbd5e1" stroke-width="2"/>')
                parts.append(f'  <circle cx="{gx + 16}" cy="{pipe_y}" r="4.5" fill="#38bdf8"/>')
                parts.append(f'  <circle cx="{gx + 32}" cy="{pipe_y}" r="3.5" fill="#ef4444"/>')
                parts.append(f'  <circle cx="{gx + 46}" cy="{pipe_y}" r="4.0" fill="#f97316"/>')
            else:
                px_w = self.x_road_start + 26
                if getattr(self.sec, "has_water_pipe", True):
                    parts.append(f'  <circle cx="{px_w}" cy="{pipe_y}" r="6.5" fill="#38bdf8" stroke="#0284c7" stroke-width="2"/>')
                if getattr(self.sec, "has_telecom_pipe", True):
                    parts.append(f'  <circle cx="{px_w + 22}" cy="{pipe_y}" r="4.5" fill="#fca5a5" stroke="#dc2626" stroke-width="1.8"/>')
                if getattr(self.sec, "has_power_cable", True):
                    parts.append(f'  <circle cx="{px_w + 42}" cy="{pipe_y}" r="5.0" fill="#fdba74" stroke="#ea580c" stroke-width="1.8"/>')
            if getattr(self.sec, "has_sewer_pipe", False):
                sx = self.x_road_start + self.road_width_px * 0.5
                parts.append(f'  <circle cx="{sx}" cy="{pipe_y}" r="9.5" fill="#292524" stroke="#78716c" stroke-width="2.5"/>')
            dx = self.x_road_start + self.road_width_px - 34
            if getattr(self.sec, "has_drainage_pipe", True):
                parts.append(f'  <circle cx="{dx}" cy="{pipe_y}" r="8.0" fill="#1e293b" stroke="#15803d" stroke-width="2.2"/>')
            if getattr(self.sec, "has_gas_pipe", True):
                parts.append(f'  <circle cx="{dx - 26}" cy="{pipe_y}" r="4.8" fill="#fef08a" stroke="#eab308" stroke-width="1.8"/>')

        return "\n".join(parts)

    def _render_furniture_and_trees(self):
        parts = ['  <!-- Urban Furniture, Trees & Lighting -->']
        cur_x = self.x_road_start

        for elem in self.sec.elements:
            ew_px = elem.width * self.ppm
            mid_x = cur_x + ew_px / 2
            base_y = self.y_ground - (elem.elevation * self.ppm)

            # 1. ORGANİK MİMARİ AĞAÇ (Botanical Tree)
            if elem.has_trees:
                trunk_h = 2.6 * self.ppm
                canopy_r = 2.1 * self.ppm
                # Döküm kök ızgarası
                parts.append(f'  <rect x="{mid_x - 16}" y="{base_y - 1.5}" width="32" height="3" fill="#1e293b"/>')
                # Ağaç gövdesi
                parts.append(
                    f'  <path d="M {mid_x - 3.5} {base_y} L {mid_x - 2.5} {base_y - trunk_h} '
                    f'Q {mid_x - 10} {base_y - trunk_h - 15} {mid_x - 18} {base_y - trunk_h - 25} '
                    f'M {mid_x + 2.5} {base_y - trunk_h} Q {mid_x + 10} {base_y - trunk_h - 15} {mid_x + 18} {base_y - trunk_h - 25} '
                    f'M {mid_x + 3.5} {base_y} L {mid_x + 2.5} {base_y - trunk_h} Z" '
                    f'fill="#78350f" stroke="#451a03" stroke-width="1.2"/>'
                )
                # Organik taç katmanları
                cy = base_y - trunk_h - canopy_r + 10
                parts.append(
                    f'  <circle cx="{mid_x}" cy="{cy}" r="{canopy_r}" fill="url(#treeCanopy1)" stroke="#14532d" stroke-width="1.5"/>'
                )
                parts.append(
                    f'  <circle cx="{mid_x - canopy_r * 0.4}" cy="{cy - canopy_r * 0.2}" r="{canopy_r * 0.6}" fill="#86efac" opacity="0.35"/>'
                )

            # 2. MODERN LED AYDINLATMA VE IŞIK KONİSİ
            if elem.has_lighting:
                pole_h = 4.8 * self.ppm
                pole_x = cur_x + 10
                # Direk
                parts.append(f'  <line x1="{pole_x}" y1="{base_y}" x2="{pole_x}" y2="{base_y - pole_h}" stroke="#1e293b" stroke-width="3"/>')
                # Armatür kolu
                parts.append(
                    f'  <path d="M {pole_x} {base_y - pole_h} Q {pole_x + 16} {base_y - pole_h - 12} {pole_x + 26} {base_y - pole_h + 4}" '
                    f'fill="none" stroke="#1e293b" stroke-width="2.5"/>'
                )
                # Armatür
                parts.append(
                    f'  <rect x="{pole_x + 20}" y="{base_y - pole_h + 3}" width="12" height="4" rx="1.5" fill="#facc15" stroke="#ca8a04"/>'
                )
                # Işık Konisi
                parts.append(
                    f'  <polygon points="{pole_x + 26},{base_y - pole_h + 7} {pole_x - 15},{base_y} {pole_x + 65},{base_y}" '
                    f'fill="url(#lightConeGrad)"/>'
                )

            # 3. ŞIK OTURMA BANKI (Bench)
            if elem.has_bench:
                bx = mid_x - 14
                parts.append(f'  <rect x="{bx}" y="{base_y - 14}" width="28" height="3" fill="#b45309" stroke="#78350f" stroke-width="0.8"/>')
                parts.append(f'  <rect x="{bx}" y="{base_y - 8}" width="28" height="3" fill="#b45309" stroke="#78350f" stroke-width="0.8"/>')
                parts.append(f'  <line x1="{bx + 4}" y1="{base_y}" x2="{bx + 4}" y2="{base_y - 14}" stroke="#1e293b" stroke-width="2"/>')
                parts.append(f'  <line x1="{bx + 24}" y1="{base_y}" x2="{bx + 24}" y2="{base_y - 14}" stroke="#1e293b" stroke-width="2"/>')

            # 4. CAM OTOBÜS DURAĞI KABİNİ (Bus Shelter)
            if elem.has_bus_shelter:
                sh_w = 42
                sh_h = 2.4 * self.ppm
                sh_x = cur_x + ew_px - sh_w - 6
                # Çatı
                parts.append(f'  <rect x="{sh_x - 4}" y="{base_y - sh_h}" width="{sh_w + 8}" height="5" rx="2" fill="#334155"/>')
                # Cam paneller
                parts.append(
                    f'  <rect x="{sh_x}" y="{base_y - sh_h + 5}" width="{sh_w}" height="{sh_h - 5}" '
                    f'fill="#e0f2fe" opacity="0.6" stroke="#0284c7" stroke-width="1"/>'
                )
                # Bus Stop Sign
                lang = getattr(self.sec, "language", get_language())
                parts.append(f'  <circle cx="{sh_x + 8}" cy="{base_y - sh_h - 10}" r="6" fill="#ef4444" stroke="#b91c1c"/>')
                parts.append(f'  <text x="{sh_x + 8}" y="{base_y - sh_h - 7}" font-family="sans-serif" font-size="8" font-weight="bold" fill="#ffffff" text-anchor="middle">{tr_text("canvas_bus_sign", lang)}</text>')

            # 5. BİSİKLET PARK DEMİRLERİ (U-Racks)
            if elem.has_bike_rack:
                for roff in (-8, 8):
                    rx = mid_x + roff
                    parts.append(
                        f'  <path d="M {rx - 6} {base_y} L {rx - 6} {base_y - 20} Q {rx} {base_y - 26} {rx + 6} {base_y - 20} L {rx + 6} {base_y}" '
                        f'fill="none" stroke="#475569" stroke-width="2.5"/>'
                    )

            cur_x += ew_px

        return "\n".join(parts)

    def _render_scale_figures(self):
        parts = ['  <!-- Scale Figures, Vehicles & Cyclists -->']
        cur_x = self.x_road_start

        for elem in self.sec.elements:
            ew_px = elem.width * self.ppm
            mid_x = cur_x + ew_px / 2
            base_y = self.y_ground - (elem.elevation * self.ppm)

            # İnsanlar
            if elem.pedestrian_count > 0:
                p_offsets = [0] if elem.pedestrian_count == 1 else [-16, 16] if elem.pedestrian_count == 2 else [-22, 0, 22]
                for p_idx, p_off in enumerate(p_offsets):
                    parts.append(self._svg_detailed_pedestrian(mid_x + p_off, base_y, variant=p_idx % 3))

            # Bisikletli
            if elem.cyclist_count > 0:
                parts.append(self._svg_detailed_cyclist(mid_x, base_y))

            # Araçlar
            if elem.vehicle_type == "car":
                parts.append(self._svg_detailed_car(mid_x, base_y))
            elif elem.vehicle_type == "bus":
                parts.append(self._svg_detailed_bus(mid_x, base_y))

            cur_x += ew_px

        return "\n".join(parts)

    def _svg_detailed_pedestrian(self, x, y, variant=0):
        """Gerçekçi ölçekli insan silüeti."""
        scale = self.ppm / 30.0
        h_total = 1.75 * self.ppm
        head_r = 4.8 * scale
        head_y = y - h_total + head_r

        parts = []
        if variant == 0:
            # İş insanı / çanta taşıyan figür
            parts.append(f'  <circle cx="{x}" cy="{head_y}" r="{head_r}" fill="#0f172a"/>')
            parts.append(
                f'  <path d="M {x - 4*scale} {head_y + head_r + 2} L {x + 4*scale} {head_y + head_r + 2} '
                f'L {x + 5*scale} {y - 22*scale} L {x + 2*scale} {y} L {x} {y - 20*scale} '
                f'L {x - 3*scale} {y} L {x - 5*scale} {y - 22*scale} Z" fill="#1e293b"/>'
            )
            # Evrak çantası
            parts.append(f'  <rect x="{x + 6*scale}" y="{y - 26*scale}" width="{6*scale}" height="{9*scale}" rx="1" fill="#78350f"/>')
        elif variant == 1:
            # Koşan / sportif figür
            parts.append(f'  <circle cx="{x}" cy="{head_y}" r="{head_r}" fill="#1e293b"/>')
            parts.append(
                f'  <path d="M {x - 3*scale} {head_y + head_r + 2} L {x + 4*scale} {head_y + head_r + 2} '
                f'L {x + 8*scale} {y - 18*scale} L {x + 10*scale} {y} L {x + 5*scale} {y - 16*scale} '
                f'L {x - 6*scale} {y} L {x - 4*scale} {y - 20*scale} Z" fill="#2563eb"/>'
            )
        else:
            # Günlük yürüyen figür
            parts.append(f'  <circle cx="{x}" cy="{head_y}" r="{head_r}" fill="#334155"/>')
            parts.append(
                f'  <path d="M {x - 4*scale} {head_y + head_r + 2} L {x + 4*scale} {head_y + head_r + 2} '
                f'L {x + 4*scale} {y - 24*scale} L {x + 2*scale} {y} L {x} {y - 22*scale} '
                f'L {x - 2*scale} {y} L {x - 4*scale} {y - 24*scale} Z" fill="#475569"/>'
            )
        return "\n".join(parts)

    def _svg_detailed_cyclist(self, x, y):
        """Kasklı, modern şehir bisikletlisi silüeti."""
        scale = self.ppm / 30.0
        parts = [
            # Tekerlekler ve jantlar
            f'  <circle cx="{x - 14 * scale}" cy="{y - 9 * scale}" r="{9 * scale}" fill="#0f172a" stroke="#38bdf8" stroke-width="2"/>',
            f'  <circle cx="{x + 14 * scale}" cy="{y - 9 * scale}" r="{9 * scale}" fill="#0f172a" stroke="#38bdf8" stroke-width="2"/>',
            f'  <circle cx="{x - 14 * scale}" cy="{y - 9 * scale}" r="{3 * scale}" fill="#94a3b8"/>',
            f'  <circle cx="{x + 14 * scale}" cy="{y - 9 * scale}" r="{3 * scale}" fill="#94a3b8"/>',
            # Kadro
            f'  <path d="M {x - 14 * scale} {y - 9 * scale} L {x - 2 * scale} {y - 9 * scale} '
            f'L {x + 8 * scale} {y - 22 * scale} L {x - 5 * scale} {y - 22 * scale} Z" fill="none" stroke="#0284c7" stroke-width="2.5"/>',
            f'  <line x1="{x - 2 * scale}" y1="{y - 9 * scale}" x2="{x - 5 * scale}" y2="{y - 27 * scale}" stroke="#0284c7" stroke-width="2.5"/>',
            f'  <line x1="{x - 8 * scale}" y1="{y - 27 * scale}" x2="{x - 2 * scale}" y2="{y - 27 * scale}" stroke="#0f172a" stroke-width="3"/>',
            # Gidon
            f'  <line x1="{x + 14 * scale}" y1="{y - 9 * scale}" x2="{x + 8 * scale}" y2="{y - 28 * scale}" stroke="#0284c7" stroke-width="2.5"/>',
            f'  <line x1="{x + 6 * scale}" y1="{y - 28 * scale}" x2="{x + 12 * scale}" y2="{y - 28 * scale}" stroke="#0f172a" stroke-width="3"/>',
            # Sürücü
            f'  <circle cx="{x + 3 * scale}" cy="{y - 42 * scale}" r="{5.5 * scale}" fill="#0f172a"/>',
            # Kask
            f'  <path d="M {x - 2 * scale} {y - 43 * scale} Q {x + 3 * scale} {y - 49 * scale} {x + 9 * scale} {y - 42 * scale} Z" fill="#ef4444"/>',
            # Gövde
            f'  <path d="M {x + 2 * scale} {y - 36 * scale} L {x - 4 * scale} {y - 26 * scale} L {x} {y - 12 * scale}" fill="none" stroke="#1e293b" stroke-width="4"/>',
            # Kollar
            f'  <line x1="{x + 1 * scale}" y1="{y - 35 * scale}" x2="{x + 9 * scale}" y2="{y - 28 * scale}" stroke="#1e293b" stroke-width="2.5"/>',
        ]
        return "\n".join(parts)

    def _svg_detailed_car(self, x, y):
        """Modern sedan otomobil arka/ön detaylı kesiti."""
        w = 1.95 * self.ppm
        h = 1.48 * self.ppm
        parts = [
            # Gövde
            f'  <path d="M {x - w/2} {y - 10} Q {x - w/2} {y - h*0.55} {x - w*0.42} {y - h*0.62} '
            f'L {x - w*0.35} {y - h} L {x + w*0.35} {y - h} '
            f'L {x + w*0.42} {y - h*0.62} Q {x + w/2} {y - h*0.55} {x + w/2} {y - 10} Z" '
            f'fill="#0284c7" stroke="#0369a1" stroke-width="1.6"/>',
            # Arka / Ön Cam
            f'  <path d="M {x - w*0.33} {y - h + 5} L {x + w*0.33} {y - h + 5} '
            f'L {x + w*0.38} {y - h*0.65} L {x - w*0.38} {y - h*0.65} Z" fill="#e0f2fe" stroke="#38bdf8" stroke-width="1"/>',
            # Geniş Lastikler ve Jantlar
            f'  <rect x="{x - w/2}" y="{y - 12}" width="{w*0.16}" height="12" rx="3" fill="#0f172a"/>',
            f'  <circle cx="{x - w/2 + w*0.08}" cy="{y - 6}" r="3" fill="#94a3b8"/>',
            f'  <rect x="{x + w/2 - w*0.16}" y="{y - 12}" width="{w*0.16}" height="12" rx="3" fill="#0f172a"/>',
            f'  <circle cx="{x + w/2 - w*0.08}" cy="{y - 6}" r="3" fill="#94a3b8"/>',
            # LED Farlar
            f'  <rect x="{x - w*0.44}" y="{y - h*0.5}" width="14" height="6" rx="1.5" fill="#ef4444" stroke="#991b1b"/>',
            f'  <rect x="{x + w*0.44 - 14}" y="{y - h*0.5}" width="14" height="6" rx="1.5" fill="#ef4444" stroke="#991b1b"/>',
            # Plate
            f'  <rect x="{x - 14}" y="{y - h*0.38}" width="28" height="8" rx="1" fill="#ffffff" stroke="#0f172a" stroke-width="0.8"/>',
            f'  <text x="{x}" y="{y - h*0.38 + 6.5}" font-family="sans-serif" font-size="5" font-weight="bold" fill="#0f172a" text-anchor="middle">{tr_text("svg_car_plate", getattr(self.sec, "language", get_language()))}</text>',
            # Yan Aynalar
            f'  <polygon points="{x - w/2},{y - h*0.65} {x - w/2 - 6},{y - h*0.68} {x - w/2 - 6},{y - h*0.62}" fill="#0369a1"/>',
            f'  <polygon points="{x + w/2},{y - h*0.65} {x + w/2 + 6},{y - h*0.68} {x + w/2 + 6},{y - h*0.62}" fill="#0369a1"/>',
        ]
        return "\n".join(parts)

    def _svg_detailed_bus(self, x, y):
        """Modern low-floor transit bus section."""
        w = 2.65 * self.ppm
        h = 3.25 * self.ppm
        lang = getattr(self.sec, "language", get_language())
        parts = [
            f'  <rect x="{x - w/2}" y="{y - h}" width="{w}" height="{h - 6}" rx="8" fill="#16a34a" stroke="#14532d" stroke-width="2"/>',
            f'  <rect x="{x - w*0.3}" y="{y - h - 7}" width="{w*0.6}" height="7" rx="2" fill="#334155"/>',
            f'  <rect x="{x - w*0.38}" y="{y - h + 5}" width="{w*0.76}" height="10" rx="2" fill="#0f172a"/>',
            f'  <text x="{x}" y="{y - h + 13}" font-family="sans-serif" font-size="7" font-weight="bold" fill="#facc15" text-anchor="middle">{tr_text("svg_bus_led", lang)}</text>',
            f'  <rect x="{x - w*0.44}" y="{y - h + 18}" width="{w*0.88}" height="{h*0.46}" rx="4" fill="#e0f2fe" stroke="#0284c7" stroke-width="1.2"/>',
            f'  <circle cx="{x - w*0.25}" cy="{y - h + 38}" r="5" fill="#334155" opacity="0.6"/>',
            f'  <circle cx="{x + w*0.25}" cy="{y - h + 38}" r="5" fill="#334155" opacity="0.6"/>',
            f'  <rect x="{x - w*0.48}" y="{y - 12}" width="{w*0.16}" height="12" rx="3" fill="#0f172a"/>',
            f'  <rect x="{x + w*0.48 - w*0.16}" y="{y - 12}" width="{w*0.16}" height="12" rx="3" fill="#0f172a"/>',
            f'  <rect x="{x - w*0.42}" y="{y - 20}" width="16" height="7" rx="1.5" fill="#fef08a" stroke="#ca8a04"/>',
            f'  <rect x="{x + w*0.42 - 16}" y="{y - 20}" width="16" height="7" rx="1.5" fill="#fef08a" stroke="#ca8a04"/>',
            f'  <rect x="{x - 16}" y="{y - 16}" width="32" height="7" fill="#ffffff" stroke="#0f172a"/>',
            f'  <text x="{x}" y="{y - 11}" font-family="sans-serif" font-size="5" font-weight="bold" fill="#0f172a" text-anchor="middle">{tr_text("svg_bus_plate", lang)}</text>',
        ]
        return "\n".join(parts)

    def _render_dimensions(self):
        parts = ['  <!-- Architectural Dimension Chain & Right-of-Way -->']
        dim_y1 = self.y_ground + 60
        dim_y2 = self.y_ground + 105

        cur_x = self.x_road_start
        for i, elem in enumerate(self.sec.elements):
            ew_px = elem.width * self.ppm
            x1 = cur_x
            x2 = cur_x + ew_px
            mid = (x1 + x2) / 2

            # Tanıklık çizgileri
            parts.append(f'  <line x1="{x1}" y1="{self.y_ground + 44}" x2="{x1}" y2="{dim_y1 + 12}" stroke="#94a3b8" stroke-width="0.8"/>')
            parts.append(f'  <line x1="{x2}" y1="{self.y_ground + 44}" x2="{x2}" y2="{dim_y1 + 12}" stroke="#94a3b8" stroke-width="0.8"/>')

            # Ölçü çizgisi ve mimari 45° çentikler
            parts.append(f'  <line x1="{x1}" y1="{dim_y1}" x2="{x2}" y2="{dim_y1}" stroke="#1e293b" stroke-width="1.2"/>')
            parts.append(f'  <line x1="{x1 - 3}" y1="{dim_y1 + 3}" x2="{x1 + 3}" y2="{dim_y1 - 3}" stroke="#1e293b" stroke-width="2"/>')
            parts.append(f'  <line x1="{x2 - 3}" y1="{dim_y1 + 3}" x2="{x2 + 3}" y2="{dim_y1 - 3}" stroke="#1e293b" stroke-width="2"/>')

            # Genişlik Metni
            parts.append(
                f'  <text x="{mid}" y="{dim_y1 - 6}" font-family="sans-serif" font-size="11.5" font-weight="bold" '
                f'fill="#0f172a" text-anchor="middle">{elem.width:.2f} m</text>'
            )

            # Eleman Etiketi (Dar alanlarda alternatif basamaklandırma ile çakışmayı önle!)
            label_y = dim_y1 + 20 if (i % 2 == 0) else dim_y1 + 33
            lbl = escape(elem.label)
            parts.append(
                f'  <text x="{mid}" y="{label_y}" font-family="sans-serif" font-size="9" font-weight="500" '
                f'fill="#475569" text-anchor="middle">{lbl}</text>'
            )

            # Enine Eğim Okları (%2 Drenaj)
            if elem.slope_pct != 0.0 and ew_px > 40:
                parts.append(
                    f'  <text x="{mid}" y="{self.y_ground - 4}" font-family="sans-serif" font-size="7.5" '
                    f'fill="#94a3b8" text-anchor="middle">◄ %{abs(elem.slope_pct):.1f}</text>'
                )

            cur_x += ew_px

        # Kırmızı Çizgi Master Ölçüsü
        rx1 = self.x_road_start
        rx2 = self.x_road_start + self.road_width_px
        rmid = (rx1 + rx2) / 2

        parts.append(f'  <line x1="{rx1}" y1="{dim_y1 + 16}" x2="{rx1}" y2="{dim_y2 + 12}" stroke="#dc2626" stroke-width="1.2" stroke-dasharray="4,2"/>')
        parts.append(f'  <line x1="{rx2}" y1="{dim_y1 + 16}" x2="{rx2}" y2="{dim_y2 + 12}" stroke="#dc2626" stroke-width="1.2" stroke-dasharray="4,2"/>')
        parts.append(f'  <line x1="{rx1}" y1="{dim_y2}" x2="{rx2}" y2="{dim_y2}" stroke="#dc2626" stroke-width="2"/>')
        parts.append(f'  <line x1="{rx1 - 5}" y1="{dim_y2 + 5}" x2="{rx1 + 5}" y2="{dim_y2 - 5}" stroke="#dc2626" stroke-width="2.5"/>')
        parts.append(f'  <line x1="{rx2 - 5}" y1="{dim_y2 + 5}" x2="{rx2 + 5}" y2="{dim_y2 - 5}" stroke="#dc2626" stroke-width="2.5"/>')

        lang = getattr(self.sec, "language", get_language())
        parts.append(
            f'  <rect x="{rmid - 140}" y="{dim_y2 - 12}" width="280" height="24" rx="4" fill="#fef2f2" stroke="#dc2626" stroke-width="1"/>'
        )
        parts.append(
            f'  <text x="{rmid}" y="{dim_y2 + 4}" font-family="sans-serif" font-size="12" font-weight="bold" '
            f'fill="#b91c1c" text-anchor="middle">{tr_text("svg_row_width", lang, row=self.sec.right_of_way)}</text>'
        )

        return "\n".join(parts)

    def _render_title_block(self):
        parts = ['  <!-- Title & Summary Block -->']
        stats = self.sec.summary_stats()
        lang = getattr(self.sec, "language", get_language())
        parts.append(
            f'  <text x="{self.canvas_width / 2}" y="42" font-family="sans-serif" font-size="20" font-weight="bold" '
            f'letter-spacing="0.5" fill="#0f172a" text-anchor="middle">{escape(self.sec.name.upper())}</text>'
        )
        subtitle = tr_text(
            "svg_subtitle",
            lang,
            ped_p=stats["pedestrian_pct"],
            ped_m=stats["pedestrian_m"],
            veh_p=stats["vehicular_pct"],
            veh_m=stats["vehicular_m"],
            cyc_p=stats["cycling_pct"],
            cyc_m=stats["cycling_m"],
        )
        parts.append(
            f'  <text x="{self.canvas_width / 2}" y="68" font-family="sans-serif" font-size="11.5" font-weight="500" '
            f'fill="#475569" text-anchor="middle">{escape(subtitle)}</text>'
        )
        parts.append(
            f'  <line x1="{self.margin_x}" y1="84" x2="{self.canvas_width - self.margin_x}" y2="84" '
            f'stroke="#cbd5e1" stroke-width="1.2"/>'
        )
        return "\n".join(parts)
