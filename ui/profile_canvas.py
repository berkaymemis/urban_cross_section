# -*- coding: utf-8 -*-
"""UrbanCrossSection — 1/1000 Kentsel Silüet & Topografya Kesiti Tuvali (ui/profile_canvas.py).

Qt5 (QGIS 3) ve Qt6 (QGIS 4) tam uyumlu.
Kullanıcının gönderdiği jüri görseli standardında; gün batımı gökyüzü, mimari toprak taraması,
beyaz bina kütleleri, ağaç kümeleri, kotlar ve eğim yüzdeleri içeren 300 DPI mimari tuval.
"""

import math
from qgis.PyQt.QtCore import Qt, QRectF, QPointF, pyqtSignal
from qgis.PyQt.QtGui import (
    QColor,
    QFont,
    QPen,
    QBrush,
    QPainter,
    QImage,
    QLinearGradient,
    QPolygonF,
    QPainterPath,
)
from qgis.PyQt.QtWidgets import QWidget

from ..gis.compat import (
    ANTIALIASING,
    ALIGN_CENTER,
    ALIGN_LEFT,
    ALIGN_RIGHT,
    FORMAT_ARGB32,
    PEN_STYLE_DASHLINE,
    PEN_STYLE_NOPEN,
    BRUSH_STYLE_NOBRUSH,
)
from ..core.profile_model import UrbanProfile, preset_profile_hillside_aa
from ..core.i18n import get_language, normalize_lang, tr_text


class UrbanProfileCanvasWidget(QWidget):
    """1/1000 Kentsel Silüet ve Topografya A-A' / B-B' Kesiti Canlı Çizim Tuvali."""

    buildingClicked = pyqtSignal(int)

    def __init__(self, profile: UrbanProfile = None, parent=None):
        super().__init__(parent)
        self.profile = profile or preset_profile_hillside_aa()
        self.setMinimumSize(900, 360)
        self.setMouseTracking(True)

        self.margin_left = 65.0
        self.margin_right = 45.0
        self.margin_top = 55.0
        self.margin_bottom = 60.0

        self.hovered_bldg_idx = -1
        self.selected_bldg_idx = -1
        self._bldg_rects = []

    def set_profile(self, profile: UrbanProfile):
        self.profile = profile
        self.update()

    def paintEvent(self, event):
        if not self.profile:
            return

        p = QPainter(self)
        p.setRenderHint(ANTIALIASING)

        w = self.width()
        h = self.height()
        prof = self.profile

        plot_w = float(w) - self.margin_left - self.margin_right
        plot_h = float(h) - self.margin_top - self.margin_bottom

        scale_x = plot_w / max(10.0, prof.total_length)
        v_exag = max(1.0, getattr(prof, "vertical_exaggeration", 1.0))
        datum_z = prof.min_elevation
        eff_span = prof.elevation_span * v_exag + 16.0
        min_screen_z = datum_z - 8.0
        max_screen_z = datum_z + eff_span
        scale_y = plot_h / max(10.0, eff_span + 8.0)

        base_y = self.margin_top + plot_h

        def to_screen(dist: float, elev: float):
            sx = self.margin_left + dist * scale_x
            disp_z = datum_z + (elev - datum_z) * v_exag
            sy = self.margin_top + (max_screen_z - disp_z) * scale_y
            return sx, sy

        # ---------------------------------------------------------------------
        # 1. GÖKYÜZÜ (Kullanıcı görselindeki gibi gün batımı / sunset atmosferi)
        # ---------------------------------------------------------------------
        sky_grad = QLinearGradient(0, 0, 0, base_y)
        if prof.sky_theme == "sunset":
            sky_grad.setColorAt(0.0, QColor("#1e1b4b"))   # Gece mavisi
            sky_grad.setColorAt(0.35, QColor("#4338ca"))  # Derin mor
            sky_grad.setColorAt(0.65, QColor("#c026d3"))  # Magenta pembe
            sky_grad.setColorAt(0.85, QColor("#ea580c"))  # Sıcak turuncu
            sky_grad.setColorAt(1.0, QColor("#fef08a"))   # Ufuk sarısı
        elif prof.sky_theme == "golden_hour":
            sky_grad.setColorAt(0.0, QColor("#0284c7"))
            sky_grad.setColorAt(0.6, QColor("#fed7aa"))
            sky_grad.setColorAt(1.0, QColor("#f97316"))
        else:
            sky_grad.setColorAt(0.0, QColor("#e0f2fe"))
            sky_grad.setColorAt(0.6, QColor("#f0f9ff"))
            sky_grad.setColorAt(1.0, QColor("#ffffff"))

        p.fillRect(0, 0, w, int(base_y + 6), sky_grad)
        # Alt eksen ve pafta zemini temiz beyaz
        p.fillRect(0, int(base_y + 6), w, int(h - base_y - 6), QColor("#f8fafc"))

        # ---------------------------------------------------------------------
        # 2. ZEMİN VE TOPOGRAFYA DOLGUSU (Arazinin altındaki toprak profili)
        # ---------------------------------------------------------------------
        poly = QPolygonF()
        for x_m, z_m in prof.terrain_points:
            sx, sy = to_screen(x_m, z_m)
            poly.append(QPointF(sx, sy))

        end_sx, _ = to_screen(prof.total_length, 0.0)
        start_sx, _ = to_screen(0.0, 0.0)
        poly.append(QPointF(end_sx, base_y + 6))
        poly.append(QPointF(start_sx, base_y + 6))

        # Toprak gövdesi
        p.setBrush(QBrush(QColor("#78350f")))
        p.setPen(PEN_STYLE_NOPEN)
        p.drawPolygon(poly)

        # 45 Derece mimari toprak taraması (YALNIZCA POLİGON İÇİNE KIRPILMIŞ)
        p.save()
        clip_path = QPainterPath()
        clip_path.addPolygon(poly)
        p.setClipPath(clip_path)
        p.setPen(QPen(QColor("#451a03"), 0.8))
        step_hatch = 9
        for tx in range(int(self.margin_left) - int(plot_h * 2), int(w) + 100, step_hatch):
            p.drawLine(QPointF(tx, 0), QPointF(tx + plot_h * 2.5, h))
        p.restore()

        # Yüzey çizgisi (Belirgin kentsel arazi sınırı)
        p.setPen(QPen(QColor("#1c1917"), 2.4))
        p.setBrush(BRUSH_STYLE_NOBRUSH)
        for i in range(len(prof.terrain_points) - 1):
            x1, z1 = prof.terrain_points[i]
            x2, z2 = prof.terrain_points[i + 1]
            p.drawLine(QPointF(*to_screen(x1, z1)), QPointF(*to_screen(x2, z2)))

        # ---------------------------------------------------------------------
        # 3. İZOİPS KESİŞİM İŞARETLERİ & KESİŞEN İMAR YOLLARI
        # ---------------------------------------------------------------------
        crossings = getattr(prof, "contour_crossings", [])
        if crossings and prof.source_type == "contours":
            p.setBrush(QBrush(QColor("#fbbf24")))
            p.setPen(QPen(QColor("#78350f"), 1.0))
            for cx_m, cz_m in crossings:
                csx, csy = to_screen(cx_m, cz_m)
                p.drawEllipse(QPointF(csx, csy), 2.8, 2.8)

        f_road = QFont("Arial", 6)
        f_road.setBold(True)
        for road in prof.roads:
            rx, ry = to_screen(road.center_dist, road.elevation)
            rw = max(6.0, road.width * scale_x)
            p.fillRect(QRectF(rx - rw / 2, ry - 1.5, rw, 5), QColor("#334155"))
            p.setPen(QPen(QColor("#f8fafc"), 1.0))
            p.drawRect(QRectF(rx - rw / 2, ry - 1.5, rw, 5))
            if rw >= 18.0:
                p.setFont(f_road)
                p.setPen(QPen(QColor("#e2e8f0"), 1))
                p.drawText(QRectF(rx - 35, ry + 6, 70, 11), ALIGN_CENTER, road.name[:16])

        # ---------------------------------------------------------------------
        # 4. MİMARİ YAPI KÜTLELERİ (DERİNLİK SIRALI: ÖNCE SİLÜET, SONRA KESİLENLER)
        # ---------------------------------------------------------------------
        self._bldg_rects.clear()
        f_bldg = QFont("Arial", 6)
        f_bldg.setBold(True)

        # Derinlik sırası: en uzaktaki silüet önce, doğrudan kesilenler (is_cut=True) en önde
        draw_order = sorted(
            enumerate(prof.buildings),
            key=lambda pair: (
                1 if getattr(pair[1], "is_cut", True) else 0,
                -getattr(pair[1], "depth_dist", 0.0),
            ),
        )

        lang = getattr(prof, "language", get_language())
        is_tr = (normalize_lang(lang) == "tr")
        floor_tag = "K" if is_tr else "F"
        for b_idx, b in draw_order:
            is_cut = getattr(b, "is_cut", True)
            bx, by = to_screen(b.start_dist, b.top_elevation)
            z_g_s = prof.get_elevation_at(b.start_dist)
            z_g_e = prof.get_elevation_at(b.end_dist)
            z_anchor = min(b.ground_elevation, getattr(b, "ground_min_elevation", b.ground_elevation), z_g_s, z_g_e)
            _, by_ground_top = to_screen(b.start_dist, b.ground_elevation)
            _, by_ground_bot = to_screen(b.start_dist, z_anchor)

            bw = max(3.0, b.width * scale_x)
            bh_facade = max(6.0, by_ground_top - by)
            bh_total = max(bh_facade, by_ground_bot - by)

            b_rect = QRectF(bx, by, bw, bh_total)
            self._bldg_rects.append((b_idx, b_rect))

            is_hov = (b_idx == self.hovered_bldg_idx)
            is_sel = (b_idx == self.selected_bldg_idx)

            if is_cut:
                # Doğrudan kesilen ön plan yapısı: Belirgin kesit dolgusu ve kalın kontur
                p.fillRect(QRectF(bx + 2, by + 2, bw, bh_total), QColor(15, 23, 42, 65))
                fill_col = QColor("#fefce8") if is_sel else QColor("#ffffff")
                border_col = QColor("#2563eb") if is_sel else QColor("#0284c7") if is_hov else QColor("#0f172a")
                border_w = 2.2 if (is_sel or is_hov) else 1.8
            else:
                # Arka plan / sokak bakış silüeti yapısı: Zarif cephe tonlaması
                depth = getattr(b, "depth_dist", 10.0)
                fade = min(1.0, depth / 30.0)
                p.fillRect(QRectF(bx + 1.5, by + 1.5, bw, bh_total), QColor(15, 23, 42, 35))
                fill_col = QColor("#fefce8") if is_sel else QColor(241 - int(18 * fade), 245 - int(16 * fade), 249 - int(14 * fade))
                border_col = QColor("#2563eb") if is_sel else QColor("#0284c7") if is_hov else QColor("#475569")
                border_w = 2.0 if (is_sel or is_hov) else 1.1

            p.setBrush(QBrush(fill_col))
            p.setPen(QPen(border_col, border_w))
            p.drawRect(b_rect)

            # Eğimli zeminde subbasman / temel bandı
            if by_ground_bot > by_ground_top + 1.5:
                p.fillRect(
                    QRectF(bx + 0.8, by_ground_top, max(1.0, bw - 1.6), by_ground_bot - by_ground_top),
                    QColor("#94a3b8") if is_cut else QColor("#cbd5e1"),
                )

            # Kat çizgileri ve cephe pencere ritmi
            if b.floors > 1 and bh_facade >= 8.0:
                p.setPen(QPen(QColor("#cbd5e1") if is_cut else QColor("#94a3b8"), 0.8))
                floor_px = bh_facade / float(b.floors)
                for fl in range(1, b.floors):
                    fy = by + fl * floor_px
                    p.drawLine(QPointF(bx + 1, fy), QPointF(bx + bw - 1, fy))
                    if not is_cut and bw >= 16.0 and floor_px >= 6.0:
                        # Silüet cephesinde sade mimari pencere ritmi
                        p.fillRect(QRectF(bx + bw * 0.20, fy - floor_px * 0.7, bw * 0.22, floor_px * 0.45), QColor(148, 163, 184, 110))
                        p.fillRect(QRectF(bx + bw * 0.58, fy - floor_px * 0.7, bw * 0.22, floor_px * 0.45), QColor(148, 163, 184, 110))

            # Çatı parapeti harpuştası
            p.setPen(QPen(QColor("#0f172a") if is_cut else QColor("#334155"), 2.2 if is_cut else 1.4))
            p.drawLine(QPointF(bx - 1.5, by), QPointF(bx + bw + 1.5, by))

            # Floor badge (e.g. "4F" / "4K")
            if bw >= 12.0:
                p.setFont(f_bldg)
                p.setPen(QPen(QColor("#1e293b") if is_cut else QColor("#475569"), 1))
                p.drawText(QRectF(bx, by + 2, bw, 12), ALIGN_CENTER, f"{b.floors}{floor_tag}")

        if not prof.buildings and prof.source_type != "preset":
            msg_w = min(500.0, plot_w - 40.0)
            msg_rect = QRectF(self.margin_left + (plot_w - msg_w) / 2.0, base_y - 36, msg_w, 22)
            p.fillRect(msg_rect, QColor(15, 23, 42, 165))
            p.setPen(QPen(QColor("#38bdf8"), 1))
            p.drawRect(msg_rect)
            p.setFont(f_bldg)
            p.setPen(QPen(QColor("#f8fafc"), 1))
            p.drawText(
                msg_rect,
                ALIGN_CENTER,
                tr_text("prof_empty_banner", lang),
            )

        # ---------------------------------------------------------------------
        # 5. BİTKİ ÖRTÜSÜ VE BOTANİK AĞAÇ KÜMELERİ
        # ---------------------------------------------------------------------
        for v in prof.vegetation:
            vx, vy = to_screen(v.center_dist, v.ground_elevation)
            t_rad = max(5.0, min(9.5, 2.0 * scale_y))
            t_h = max(8.0, v.tree_height * (scale_y / 2.6))

            # Gövde ve çatal dallar
            p.setPen(QPen(QColor("#451a03"), 1.5))
            p.drawLine(QPointF(vx, vy), QPointF(vx, vy - t_h))
            p.drawLine(QPointF(vx, vy - t_h * 0.6), QPointF(vx - 4, vy - t_h - 1))
            p.drawLine(QPointF(vx, vy - t_h * 0.6), QPointF(vx + 4, vy - t_h - 1))

            # Doğal botanik çok loblu yaprak tacı
            cy_t = vy - t_h - t_rad * 0.6
            p.setPen(QPen(QColor("#14532d"), 0.9))
            p.setBrush(QBrush(QColor("#15803d")))
            p.drawEllipse(QPointF(vx - t_rad * 0.55, cy_t + 2), t_rad * 0.72, t_rad * 0.68)
            p.setBrush(QBrush(QColor("#16a34a")))
            p.drawEllipse(QPointF(vx + t_rad * 0.55, cy_t + 2), t_rad * 0.72, t_rad * 0.68)
            p.setBrush(QBrush(QColor("#22c55e")))
            p.drawEllipse(QPointF(vx, cy_t - 3), t_rad * 0.85, t_rad * 0.80)

        # ---------------------------------------------------------------------
        # 6. EĞİM OKLARI VE KRİTİK EŞİK VURGUSU (> %20 İMAR SINIRI)
        # ---------------------------------------------------------------------
        f_slope = QFont("Arial", 7)
        f_slope.setBold(True)
        p.setFont(f_slope)

        for sl in prof.calculate_slopes():
            sx, sy = to_screen(sl["mid_dist"], sl["mid_elev"])
            pct = sl["slope_pct"]
            is_crit = sl.get("is_critical", False) or abs(pct) >= prof.critical_slope_threshold

            if is_crit:
                p.fillRect(QRectF(sx - 38, sy + 12, 76, 16), QColor("#dc2626"))
                p.setPen(QPen(QColor("#ffffff"), 1))
                p.drawText(QRectF(sx - 38, sy + 12, 76, 16), ALIGN_CENTER, tr_text("prof_crit_badge", lang, pct=abs(pct)))
            elif abs(pct) >= 3.0:
                p.setPen(QPen(QColor("#fef08a"), 1))
                p.drawText(QRectF(sx - 35, sy + 16, 70, 14), ALIGN_CENTER, tr_text("prof_slope_badge", lang, pct=abs(pct)))

        # 7. Title, Metadata & Compact Legend
        is_daylight = (prof.sky_theme == "daylight")
        title_col = QColor("#0f172a") if is_daylight else QColor("#ffffff")
        sub_col = QColor("#0369a1") if is_daylight else QColor("#fcd34d")

        f_title = QFont("Arial", 16)
        f_title.setBold(True)
        p.setFont(f_title)
        p.setPen(QPen(title_col, 1))
        p.drawText(QRectF(self.margin_left + 10, 12, 460, 26), ALIGN_LEFT, prof.title)

        f_sub = QFont("Arial", 7)
        p.setFont(f_sub)
        p.setPen(QPen(sub_col, 1))
        stats = prof.get_statistics()
        l_dir = getattr(prof, "look_direction", "auto")
        look_lbl = tr_text(f"look_short_{l_dir}", lang, d=prof.look_depth)
        sub_text = tr_text(
            "prof_sub_line",
            lang,
            src=prof.source_layer_name,
            look=look_lbl,
            ex=v_exag,
            len=prof.total_length,
            ms=stats.get("max_slope_pct", 0.0),
            min_z=stats.get("min_elevation", 0.0),
            max_z=stats.get("max_elevation", 0.0),
        )
        p.drawText(QRectF(self.margin_left + 12, 39, max(400.0, plot_w - 220), 16), ALIGN_LEFT, sub_text)

        # Top-right compact legend (Cut vs Elevation)
        if prof.buildings:
            leg_x = w - self.margin_right - 195
            p.fillRect(QRectF(leg_x, 12, 190, 22), QColor(15, 23, 42, 140))
            p.fillRect(QRectF(leg_x + 8, 17, 10, 10), QColor("#ffffff"))
            p.setPen(QPen(QColor("#0f172a"), 1.2))
            p.drawRect(QRectF(leg_x + 8, 17, 10, 10))
            p.setPen(QPen(QColor("#f8fafc"), 1))
            p.drawText(QRectF(leg_x + 22, 16, 65, 14), ALIGN_LEFT, tr_text("prof_legend_cut", lang))

            p.fillRect(QRectF(leg_x + 86, 17, 10, 10), QColor("#cbd5e1"))
            p.setPen(QPen(QColor("#64748b"), 1.0))
            p.drawRect(QRectF(leg_x + 86, 17, 10, 10))
            p.setPen(QPen(QColor("#f8fafc"), 1))
            p.drawText(QRectF(leg_x + 100, 16, 85, 14), ALIGN_LEFT, tr_text("prof_legend_sil", lang))

        # ---------------------------------------------------------------------
        # 8. YÜKSEKLİK VE MESAFE EKSENİ (ÖLÇÜ KOTLARI)
        # ---------------------------------------------------------------------
        f_axis = QFont("Arial", 7)
        f_axis.setBold(True)
        p.setFont(f_axis)

        z_step = 20.0 if prof.elevation_span > 60 else 10.0 if prof.elevation_span > 20 else 5.0
        cur_z = math.floor(prof.min_elevation / z_step) * z_step
        while cur_z <= prof.max_elevation + 10.0:
            _, gy = to_screen(0.0, cur_z)
            if self.margin_top <= gy <= base_y:
                pen_grid = QPen(QColor("#64748b") if is_daylight else QColor("#94a3b8"), 0.6)
                pen_grid.setStyle(PEN_STYLE_DASHLINE)
                p.setPen(pen_grid)
                p.drawLine(QPointF(self.margin_left - 6, gy), QPointF(w - self.margin_right, gy))

                p.fillRect(QRectF(self.margin_left - 58, gy - 8, 48, 16), QColor(15, 23, 42, 130) if not is_daylight else QColor(241, 245, 249, 220))
                p.setPen(QPen(title_col, 1))
                p.drawText(QRectF(self.margin_left - 56, gy - 7, 45, 14), ALIGN_RIGHT, f"+{cur_z:.0f}m")
            cur_z += z_step

        # Başlangıç A ve Bitiş B Noktası Kot Rozetleri
        if prof.terrain_points:
            z_a = prof.terrain_points[0][1]
            z_b = prof.terrain_points[-1][1]
            _, sy_a = to_screen(0.0, z_a)
            _, sy_b = to_screen(prof.total_length, z_b)

            f_ab = QFont("Arial", 7)
            f_ab.setBold(True)
            p.setFont(f_ab)
            # A Noktası Rozeti
            p.fillRect(QRectF(self.margin_left + 4, sy_a - 24, 72, 16), QColor(15, 23, 42, 195))
            p.setPen(QPen(QColor("#38bdf8"), 1))
            p.drawText(QRectF(self.margin_left + 4, sy_a - 24, 72, 16), ALIGN_CENTER, f"A: +{z_a:.1f}m")

            # B Noktası Rozeti
            p.fillRect(QRectF(w - self.margin_right - 76, sy_b - 24, 72, 16), QColor(15, 23, 42, 195))
            p.setPen(QPen(QColor("#38bdf8"), 1))
            p.drawText(QRectF(w - self.margin_right - 76, sy_b - 24, 72, 16), ALIGN_CENTER, f"B: +{z_b:.1f}m")

        # Mesafe Ekseni Çizgisi ve Metrajlar
        p.setPen(QPen(QColor("#334155"), 1.5))
        p.drawLine(QPointF(self.margin_left, base_y + 8), QPointF(w - self.margin_right, base_y + 8))

        d_step = 200.0 if prof.total_length > 1500 else 100.0 if prof.total_length > 400 else 50.0
        cur_d = 0.0
        p.setPen(QPen(QColor("#1e293b"), 1))
        while cur_d <= prof.total_length + 0.1:
            dx, _ = to_screen(cur_d, 0.0)
            p.drawLine(QPointF(dx, base_y + 5), QPointF(dx, base_y + 11))
            p.drawText(QRectF(dx - 30, base_y + 14, 60, 14), ALIGN_CENTER, f"{cur_d:.0f}m")
            cur_d += d_step

        p.end()

    def mousePressEvent(self, event):
        pos = event.pos()
        pt = QPointF(pos)
        for idx, rect in self._bldg_rects:
            if rect.contains(pt):
                self.selected_bldg_idx = idx
                self.buildingClicked.emit(idx)
                self.update()
                return
        self.selected_bldg_idx = -1
        self.update()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        pos = event.pos()
        pt = QPointF(pos)
        new_hov = -1
        for idx, rect in self._bldg_rects:
            if rect.contains(pt):
                new_hov = idx
                break
        if new_hov != self.hovered_bldg_idx:
            self.hovered_bldg_idx = new_hov
            self.update()
        super().mouseMoveEvent(event)

    def export_to_image(self, filepath: str, dpi: int = 300) -> str:
        scale_factor = dpi / 96.0
        out_w = int(self.width() * scale_factor)
        out_h = int(self.height() * scale_factor)

        img = QImage(out_w, out_h, FORMAT_ARGB32)
        img.setDotsPerMeterX(int(dpi / 0.0254))
        img.setDotsPerMeterY(int(dpi / 0.0254))
        img.fill(QColor(255, 255, 255))

        painter = QPainter(img)
        painter.setRenderHint(ANTIALIASING)
        painter.scale(scale_factor, scale_factor)
        self.render(painter)
        painter.end()

        img.save(filepath, "PNG")
        return filepath
