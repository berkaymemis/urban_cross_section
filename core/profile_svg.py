# -*- coding: utf-8 -*-
"""UrbanCrossSection — 1/1000 Kentsel A-B Kesiti Vektörel SVG Üreteci (core/profile_svg.py).

Saf Python: Hiçbir qgis veya PyQt bağımlılığı içermez.
Jüri paftaları, Illustrator, Photoshop ve CAD için 1/1000 ölçekli mimari SVG dışa aktarımı.
"""

import math
from html import escape
from typing import Optional
from .profile_model import UrbanProfile
from .i18n import get_language, tr_text


class SvgUrbanProfileExporter:
    """1/1000 Kentsel Silüet ve Topografya A-B Kesiti SVG Üreteci."""

    def __init__(self, profile: UrbanProfile):
        self.profile = profile

    def render_to_svg(self, width_px: int = 1400, height_px: int = 400) -> str:
        prof = self.profile
        margin_left = 70.0
        margin_right = 50.0
        margin_top = 60.0
        margin_bottom = 70.0

        plot_w = float(width_px) - margin_left - margin_right
        plot_h = float(height_px) - margin_top - margin_bottom

        # Ölçek çarpanları (X: Metre -> Piksel, Y: Metre -> Piksel)
        scale_x = plot_w / max(1.0, prof.total_length)
        v_exag = max(1.0, getattr(prof, "vertical_exaggeration", 1.0))
        datum_z = prof.min_elevation
        eff_span = prof.elevation_span * v_exag + 16.0
        min_screen_z = datum_z - 8.0
        max_screen_z = datum_z + eff_span
        scale_y = plot_h / max(1.0, eff_span + 8.0)

        def to_screen(dist: float, elev: float):
            sx = margin_left + dist * scale_x
            disp_z = datum_z + (elev - datum_z) * v_exag
            sy = margin_top + (max_screen_z - disp_z) * scale_y
            return sx, sy

        base_y = margin_top + plot_h

        lines = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width_px} {height_px}" '
            f'width="{width_px}" height="{height_px}">',
            '<defs>',
        ]

        # 1. Gökyüzü Gradyanları (Kullanıcı görselindeki gibi gün batımı / sunset)
        if prof.sky_theme == "sunset":
            lines.extend([
                '  <linearGradient id="skyGrad" x1="0" y1="0" x2="0" y2="1">',
                '    <stop offset="0%" stop-color="#312e81"/>',
                '    <stop offset="35%" stop-color="#4f46e5"/>',
                '    <stop offset="65%" stop-color="#db2777"/>',
                '    <stop offset="85%" stop-color="#ea580c"/>',
                '    <stop offset="100%" stop-color="#fef08a"/>',
                '  </linearGradient>',
            ])
        elif prof.sky_theme == "golden_hour":
            lines.extend([
                '  <linearGradient id="skyGrad" x1="0" y1="0" x2="0" y2="1">',
                '    <stop offset="0%" stop-color="#38bdf8"/>',
                '    <stop offset="50%" stop-color="#fed7aa"/>',
                '    <stop offset="100%" stop-color="#f97316"/>',
                '  </linearGradient>',
            ])
        else:
            lines.extend([
                '  <linearGradient id="skyGrad" x1="0" y1="0" x2="0" y2="1">',
                '    <stop offset="0%" stop-color="#e0f2fe"/>',
                '    <stop offset="60%" stop-color="#f0f9ff"/>',
                '    <stop offset="100%" stop-color="#ffffff"/>',
                '  </linearGradient>',
            ])

        # 2. Zemin Tarama Deseni (Toprak & Jeoloji)
        lines.extend([
            '  <pattern id="soilHatch" width="12" height="12" patternTransform="rotate(45 0 0)" patternUnits="userSpaceOnUse">',
            '    <line x1="0" y1="0" x2="0" y2="12" stroke="#451a03" stroke-width="0.8" opacity="0.35"/>',
            '  </pattern>',
            '  <filter id="bldgShadow" x="-5%" y="-5%" width="115%" height="115%">',
            '    <feDropShadow dx="2" dy="2" stdDeviation="2" flood-color="#0f172a" flood-opacity="0.25"/>',
            '  </filter>',
            '</defs>',
            '<!-- SKY -->',
            f'<rect x="0" y="0" width="{width_px}" height="{height_px}" fill="url(#skyGrad)"/>',
        ])

        # 3. ZEMİN VE TOPOGRAFYA DOLGUSU (Arazinin altındaki toprak katmanı)
        terrain_poly = []
        for x_m, z_m in prof.terrain_points:
            sx, sy = to_screen(x_m, z_m)
            terrain_poly.append(f"{sx:.1f},{sy:.1f}")

        # Poligonu alt sınıra kapat
        end_sx, _ = to_screen(prof.total_length, 0.0)
        start_sx, _ = to_screen(0.0, 0.0)
        terrain_closed = list(terrain_poly)
        terrain_closed.append(f"{end_sx:.1f},{base_y:.1f}")
        terrain_closed.append(f"{start_sx:.1f},{base_y:.1f}")

        pts_str = " ".join(terrain_closed)
        lines.append('<!-- TERRAIN SOIL BODY -->')
        lines.append(f'<polygon points="{pts_str}" fill="#78350f" opacity="0.92"/>')
        lines.append(f'<polygon points="{pts_str}" fill="url(#soilHatch)"/>')

        # Arazi yüzeyi belirgin kontur çizgisi
        surf_pts = " ".join(terrain_poly)
        lines.append(f'<polyline points="{surf_pts}" fill="none" stroke="#292524" stroke-width="2.5" stroke-linejoin="round"/>')

        # 4. KESİŞEN YOLLAR (Yol platformları ve teraslar)
        for road in prof.roads:
            rx, ry = to_screen(road.center_dist, road.elevation)
            rw = road.width * scale_x
            lines.append(f'<rect x="{rx - rw/2:.1f}" y="{ry:.1f}" width="{rw:.1f}" height="4" fill="#334155" stroke="#0f172a" stroke-width="1"/>')

        # 5. MİMARİ YAPI KÜTLELERİ (DERİNLİK SIRALI: ÖNCE SİLÜET, SONRA KESİLENLER)
        lines.append('<!-- BUILDING MASSES -->')
        draw_order = sorted(
            prof.buildings,
            key=lambda b: (1 if getattr(b, "is_cut", True) else 0, -getattr(b, "depth_dist", 0.0)),
        )
        for b in draw_order:
            is_cut = getattr(b, "is_cut", True)
            bx, by = to_screen(b.start_dist, b.top_elevation)
            z_anchor = min(
                b.ground_elevation,
                getattr(b, "ground_min_elevation", b.ground_elevation),
                prof.get_elevation_at(b.start_dist),
                prof.get_elevation_at(b.end_dist),
            )
            _, by_ground_bot = to_screen(b.start_dist, z_anchor)
            bw = max(2.5, b.width * scale_x)
            bh = max(6.0, by_ground_bot - by)

            fill_col = b.facade_color if is_cut else "#e2e8f0"
            stroke_col = b.outline_color if is_cut else "#64748b"
            stroke_w = "1.8" if is_cut else "1.1"
            grp_open = '<g filter="url(#bldgShadow)">' if is_cut else '<g opacity="0.92">'

            lines.append(grp_open)
            lines.append(f'  <rect x="{bx:.1f}" y="{by:.1f}" width="{bw:.1f}" height="{bh:.1f}" fill="{fill_col}" stroke="{stroke_col}" stroke-width="{stroke_w}"/>')
            if b.floors > 1:
                floor_px = (3.0 * v_exag) * scale_y
                for fl in range(1, b.floors):
                    fy = by + fl * floor_px
                    if fy < by + bh:
                        lines.append(f'  <line x1="{bx:.1f}" y1="{fy:.1f}" x2="{bx + bw:.1f}" y2="{fy:.1f}" stroke="#cbd5e1" stroke-width="0.8"/>')
            lines.append(f'  <line x1="{bx - 2:.1f}" y1="{by:.1f}" x2="{bx + bw + 2:.1f}" y2="{by:.1f}" stroke="#0f172a" stroke-width="{2.2 if is_cut else 1.4}"/>')
            lines.append('</g>')

        # 6. BİTKİ ÖRTÜSÜ VE BOTANİK AĞAÇ KÜMELERİ
        lines.append('<!-- TREE CLUSTERS -->')
        for v in prof.vegetation:
            vx, vy = to_screen(v.center_dist, v.ground_elevation)
            t_rad = max(5.0, min(9.5, 2.0 * scale_y))
            t_h = max(8.0, v.tree_height * (scale_y / 2.6))
            cy_t = vy - t_h - t_rad * 0.6
            lines.append(f'<g opacity="0.95">')
            lines.append(f'  <line x1="{vx:.1f}" y1="{vy:.1f}" x2="{vx:.1f}" y2="{vy - t_h:.1f}" stroke="#451a03" stroke-width="1.5"/>')
            lines.append(f'  <line x1="{vx:.1f}" y1="{vy - t_h * 0.6:.1f}" x2="{vx - 4:.1f}" y2="{vy - t_h - 1:.1f}" stroke="#451a03" stroke-width="1.2"/>')
            lines.append(f'  <line x1="{vx:.1f}" y1="{vy - t_h * 0.6:.1f}" x2="{vx + 4:.1f}" y2="{vy - t_h - 1:.1f}" stroke="#451a03" stroke-width="1.2"/>')
            lines.append(f'  <ellipse cx="{vx - t_rad * 0.55:.1f}" cy="{cy_t + 2:.1f}" rx="{t_rad * 0.72:.1f}" ry="{t_rad * 0.68:.1f}" fill="#15803d" stroke="#14532d" stroke-width="0.9"/>')
            lines.append(f'  <ellipse cx="{vx + t_rad * 0.55:.1f}" cy="{cy_t + 2:.1f}" rx="{t_rad * 0.72:.1f}" ry="{t_rad * 0.68:.1f}" fill="#16a34a" stroke="#14532d" stroke-width="0.9"/>')
            lines.append(f'  <ellipse cx="{vx:.1f}" cy="{cy_t - 3:.1f}" rx="{t_rad * 0.85:.1f}" ry="{t_rad * 0.80:.1f}" fill="#22c55e" stroke="#14532d" stroke-width="0.9"/>')
            lines.append('</g>')

        # 7. Slope Labels
        lang = getattr(prof, "language", get_language())
        lines.append('<!-- SLOPE MARKERS -->')
        for sl in prof.calculate_slopes():
            sx, sy = to_screen(sl["mid_dist"], sl["mid_elev"])
            pct = sl["slope_pct"]
            if abs(pct) >= 3.0:
                arrow = tr_text("prof_slope_badge", lang, pct=abs(pct))
                lines.append(f'<text x="{sx:.1f}" y="{sy + 22:.1f}" font-family="Arial, sans-serif" font-size="8" font-weight="bold" fill="#fef08a" text-anchor="middle">{arrow}</text>')

        # 8. BAŞLIK VE ÖLÇEK (Kullanıcı görseli stili: BOLD BÜYÜK BAŞLIK)
        safe_title = escape(prof.title, quote=False)
        lines.append('<!-- TITLE -->')
        lines.append(f'<text x="{margin_left + 10:.1f}" y="38" font-family="Impact, Arial Black, sans-serif" font-size="22" letter-spacing="1" fill="#ffffff" stroke="#0f172a" stroke-width="0.8">{safe_title}</text>')

        lines.append('<!-- ELEVATION AXIS -->')
        z_step = 20.0 if prof.elevation_span > 60 else 10.0
        cur_z = math.floor(prof.min_elevation / z_step) * z_step
        while cur_z <= prof.max_elevation + 10.0:
            _, gy = to_screen(0.0, cur_z)
            if margin_top <= gy <= base_y:
                lines.append(f'<line x1="{margin_left - 8:.1f}" y1="{gy:.1f}" x2="{width_px - margin_right:.1f}" y2="{gy:.1f}" stroke="#94a3b8" stroke-dasharray="3,4" stroke-width="0.6" opacity="0.4"/>')
                lines.append(f'<text x="{margin_left - 12:.1f}" y="{gy + 3:.1f}" font-family="Arial, sans-serif" font-size="8" font-weight="bold" fill="#ffffff" text-anchor="end">+{cur_z:.0f}m</text>')
            cur_z += z_step

        # Mesafe ekseni (0m, 100m, 200m...)
        lines.append('<!-- DISTANCE AXIS -->')
        lines.append(f'<line x1="{margin_left:.1f}" y1="{base_y + 10:.1f}" x2="{width_px - margin_right:.1f}" y2="{base_y + 10:.1f}" stroke="#334155" stroke-width="1.5"/>')
        d_step = 100.0 if prof.total_length > 400 else 50.0
        cur_d = 0.0
        while cur_d <= prof.total_length + 0.1:
            dx, _ = to_screen(cur_d, 0.0)
            lines.append(f'<line x1="{dx:.1f}" y1="{base_y + 6:.1f}" x2="{dx:.1f}" y2="{base_y + 14:.1f}" stroke="#334155" stroke-width="1.5"/>')
            lines.append(f'<text x="{dx:.1f}" y="{base_y + 26:.1f}" font-family="Arial, sans-serif" font-size="8" font-weight="bold" fill="#1e293b" text-anchor="middle">{cur_d:.0f}m</text>')
            cur_d += d_step

        lines.append('</svg>')
        return "\n".join(lines)

    def save_to_file(self, filepath: str, width_px: int = 1400, height_px: int = 400) -> str:
        svg_content = self.render_to_svg(width_px, height_px)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(svg_content)
        return filepath
