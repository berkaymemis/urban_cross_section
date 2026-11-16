# -*- coding: utf-8 -*-
"""UrbanCrossSection — Streetmix Tarzı İnteraktif Mimari Kesit Tuvali (ui/canvas_widget.py).

Qt5 (QGIS 3) ve Qt6 (QGIS 4) tam uyumlu.
Doğrudan tuval üzerinden segment seçimi, [-] [+] genişlik butonları, zengin mimari zemin katmanları,
kot işaretleri, eğim okları ve çift kademeli (şerit bazlı + kırmızı çizgi) ölçülendirme.
"""

import math
from qgis.PyQt.QtCore import Qt, QSize, QRectF, QPointF, pyqtSignal
from qgis.PyQt.QtGui import (
    QColor,
    QFont,
    QPen,
    QBrush,
    QPainter,
    QImage,
    QLinearGradient,
    QRadialGradient,
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
from ..core.elements import ElementType
from ..core.i18n import get_language, normalize_lang, tr_text


class SectionCanvasWidget(QWidget):
    """Streetmix tarzı tam ekran, doğrudan manipülasyonlu 2D mimari kesit tuvali."""

    # Sinyaller
    elementClicked = pyqtSignal(int)
    elementWidthAdjusted = pyqtSignal(int, float)  # (element_index, delta_meters)
    elementDeleteRequested = pyqtSignal(int)
    utilityToggled = pyqtSignal(str)  # (utility_key: "water", "telecom", "power", "gas", "drainage", "sewer", "gallery")

    def __init__(self, section=None, parent=None):
        super().__init__(parent)
        self.section = section
        self.setMinimumSize(920, 520)
        self.setMouseTracking(True)

        self.ppm = 32.0
        self.margin_x = 45.0
        self.margin_top = 80.0
        self.margin_bottom = 145.0

        self.hovered_element_idx = -1
        self.selected_element_idx = 0
        self.hovered_action = None  # (elem_idx, "minus" | "plus" | "delete")
        self.hovered_utility_key = None

        # Tıklanabilir buton, segment ve altyapı sınırları
        self._element_rects = []
        self._btn_rects = {}  # (elem_idx, action) -> QRectF
        self._utility_rects = {}  # u_key -> (QRectF, label_str)

    def set_section(self, section):
        self.section = section
        if self.section and self.selected_element_idx >= len(self.section.elements):
            self.selected_element_idx = max(0, len(self.section.elements) - 1)
        self.update()

    def set_selected_element(self, idx):
        if self.section and 0 <= idx < len(self.section.elements):
            self.selected_element_idx = idx
            self.update()

    def mousePressEvent(self, event):
        pos = event.pos()
        pt = QPointF(pos)

        # 1. Önce segment üstündeki [-], [+] veya [x] butonlarına tıklandı mı kontrol et
        for (idx, action), rect in self._btn_rects.items():
            if rect.contains(pt):
                if action == "minus":
                    self.elementWidthAdjusted.emit(idx, -0.25)
                elif action == "plus":
                    self.elementWidthAdjusted.emit(idx, 0.25)
                elif action == "delete":
                    self.elementDeleteRequested.emit(idx)
                return

        # 2. Yeraltı altyapı borularına / galerisine tıklandı mı kontrol et (Tıkla -> Kaldır/Seç)
        for u_key, (u_rect, _u_lbl) in list(self._utility_rects.items()):
            if u_rect.contains(pt):
                if self.section and hasattr(self.section, "toggle_utility"):
                    self.section.toggle_utility(u_key)
                    self.hovered_utility_key = None
                    self.utilityToggled.emit(u_key)
                    self.update()
                return

        # 3. Şeridin kendisine tıklandı mı kontrol et
        for idx, rect in enumerate(self._element_rects):
            if rect.contains(pt):
                self.selected_element_idx = idx
                self.elementClicked.emit(idx)
                self.update()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        pos = event.pos()
        pt = QPointF(pos)

        # Buton hover kontrolü
        new_hover_action = None
        for (idx, action), rect in self._btn_rects.items():
            if rect.contains(pt):
                new_hover_action = (idx, action)
                break

        # Yeraltı altyapı hover kontrolü
        new_hover_util = None
        if new_hover_action is None:
            for u_key, (u_rect, _u_lbl) in self._utility_rects.items():
                if u_rect.contains(pt):
                    new_hover_util = u_key
                    break

        # Segment hover kontrolü
        new_hover = -1
        if new_hover_util is None:
            for idx, rect in enumerate(self._element_rects):
                if rect.contains(pt):
                    new_hover = idx
                    break

        if (
            new_hover_action != self.hovered_action
            or new_hover != self.hovered_element_idx
            or new_hover_util != self.hovered_utility_key
        ):
            self.hovered_action = new_hover_action
            self.hovered_element_idx = new_hover
            self.hovered_utility_key = new_hover_util
            self.update()

        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self.hovered_element_idx = -1
        self.hovered_action = None
        self.hovered_utility_key = None
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        """Streetmix tarzı mimari sahneyi çizen ana döngü."""
        if not self.section:
            return

        painter = QPainter(self)
        painter.setRenderHint(ANTIALIASING)

        w = self.width()
        h = self.height()
        sec = self.section
        theme = getattr(sec, "visual_theme", "architectural")

        # 1. Gökyüzü ve Atmosfer (Görsel Temaya Göre)
        sky_grad = QLinearGradient(0, 0, 0, h)
        if theme == "technical_cad":
            sky_grad.setColorAt(0.0, QColor("#ffffff"))
            sky_grad.setColorAt(1.0, QColor("#f8fafc"))
            painter.fillRect(0, 0, w, h, sky_grad)
            # İnce teknik milimetrik kareli ızgara
            painter.setPen(QPen(QColor(226, 232, 240, 120), 0.6))
            for gx in range(0, w, 24):
                painter.drawLine(gx, 0, gx, h)
            for gy in range(0, h, 24):
                painter.drawLine(0, gy, w, gy)
        elif theme == "sunset_warm":
            sky_grad.setColorAt(0.0, QColor("#fde68a"))
            sky_grad.setColorAt(0.45, QColor("#fef3c7"))
            sky_grad.setColorAt(1.0, QColor("#fffbeb"))
            painter.fillRect(0, 0, w, h, sky_grad)
        elif theme == "night_lighting":
            sky_grad.setColorAt(0.0, QColor("#0f172a"))
            sky_grad.setColorAt(0.55, QColor("#1e293b"))
            sky_grad.setColorAt(1.0, QColor("#334155"))
            painter.fillRect(0, 0, w, h, sky_grad)
        else:
            sky_grad.setColorAt(0.0, QColor("#e0f2fe"))
            sky_grad.setColorAt(0.5, QColor("#f0f9ff"))
            sky_grad.setColorAt(1.0, QColor("#ffffff"))
            painter.fillRect(0, 0, w, h, sky_grad)

        # 2. Dinamik Ölçek (Piksel / Metre)
        show_bldgs = getattr(sec, "show_buildings", True)
        bldg_visible_w_m = 5.8 if show_bldgs else 0.5
        left_sb_m = sec.left_building.setback if show_bldgs else 0.5
        right_sb_m = sec.right_building.setback if show_bldgs else 0.5
        total_span = sec.total_width + left_sb_m + right_sb_m + bldg_visible_w_m * 2
        avail_w = max(400.0, float(w - self.margin_x * 2))
        self.ppm = max(24.0, min(50.0, avail_w / total_span))

        # Zemin Y koordinatı
        y_ground = h - self.margin_bottom

        bldg_w = bldg_visible_w_m * self.ppm
        left_sb = left_sb_m * self.ppm
        right_sb = right_sb_m * self.ppm
        road_w = sec.total_width * self.ppm

        x_start = (w - (bldg_w * 2 + left_sb + road_w + right_sb)) / 2.0
        x_road = x_start + bldg_w + left_sb

        # 3. Yan Binaları Çiz (Sokağı çevreleyen mimari silüet)
        if show_bldgs:
            self._draw_streetmix_buildings(painter, sec, x_start, x_road, y_ground, bldg_w, road_w, left_sb, right_sb)

        # 4. Yol Şeritlerini ve Altyapı Tabanını Çiz
        self._draw_road_segments(painter, sec, x_road, y_ground)

        # 5. Kentsel Donatılar ve Ağaçlar
        self._draw_furniture_and_trees(painter, sec, x_road, y_ground)

        # 6. Ölçekli İnsan, Araç ve Bisikletliler
        self._draw_figures(painter, sec, x_road, y_ground)

        # 7. Streetmix Tarzı Segment Başlık Kartları ve [-] [+] Butonları (Gökyüzünde ferah konum)
        if getattr(sec, "show_cards", True):
            self._draw_streetmix_cards(painter, sec, x_road, y_ground)

        # 8. Çift Kademeli Mimari Ölçülendirme ve Kot İşaretleri
        if getattr(sec, "show_dimensions", True):
            self._draw_bottom_dimensions(painter, sec, x_road, y_ground)

        painter.end()

    # -------------------------------------------------------------------------
    # Alt Çizim Fonksiyonları (Mimari Jüri & Yarışma Standartları)
    # -------------------------------------------------------------------------

    def _draw_streetmix_buildings(self, p, sec, x_start, x_road, y_ground, bldg_w, road_w, left_sb, right_sb):
        p.save()

        # Binalar sokak kesitine orantılı 3 katlı mimari cephe (~9.5m yükseklik)
        frame_h = min(y_ground - 25, 8.5 * self.ppm)

        # Sol Bina
        lb = sec.left_building
        lb_rect = QRectF(x_start, y_ground - frame_h, bldg_w, frame_h)
        self._draw_facade(p, lb_rect, lb, is_left=True)

        # Sağ Bina
        rb = sec.right_building
        rb_x = x_road + road_w + right_sb
        rb_rect = QRectF(rb_x, y_ground - frame_h, bldg_w, frame_h)
        self._draw_facade(p, rb_rect, rb, is_left=False)

        # Ön bahçeler (Kentsel yeşil doku, çim, alçak modern çit)
        if left_sb > 2.0:
            p.fillRect(QRectF(x_start + bldg_w, y_ground - 4, left_sb, 4), QColor("#86efac"))
            p.setPen(QPen(QColor("#475569"), 1.0))
            for fx in range(int(x_start + bldg_w + 4), int(x_start + bldg_w + left_sb), 6):
                p.drawLine(QPointF(fx, y_ground - 4), QPointF(fx, y_ground - 12))
            p.drawLine(QPointF(x_start + bldg_w, y_ground - 10), QPointF(x_start + bldg_w + left_sb, y_ground - 10))

        if right_sb > 2.0:
            p.fillRect(QRectF(x_road + road_w, y_ground - 4, right_sb, 4), QColor("#86efac"))
            p.setPen(QPen(QColor("#475569"), 1.0))
            for fx in range(int(x_road + road_w + 4), int(x_road + road_w + right_sb), 6):
                p.drawLine(QPointF(fx, y_ground - 4), QPointF(fx, y_ground - 12))
            p.drawLine(QPointF(x_road + road_w, y_ground - 10), QPointF(x_road + road_w + right_sb, y_ground - 10))

        p.restore()

    def _draw_facade(self, p, rect, bldg, is_left=True):
        bx = rect.x()
        by = rect.y()
        bw = rect.width()
        bh = rect.height()

        p.save()

        # 1. Ana Cephe Duvarı (Sıcak bej/taş kaplama)
        facade_bg = QColor(bldg.facade_color) if bldg.facade_color else QColor("#f8fafc")
        p.fillRect(rect, facade_bg)
        p.setPen(QPen(QColor("#64748b"), 1.2))
        p.drawRect(rect)

        # İnce yatay taş derz çizgileri (Ashlar stone joints)
        p.setPen(QPen(QColor("#e2e8f0"), 0.8))
        joint_step = max(14, int(0.9 * self.ppm))
        for jy in range(int(by + joint_step), int(by + bh - 10), joint_step):
            p.drawLine(QPointF(bx, jy), QPointF(bx + bw, jy))

        # 2. Çatı Harpuştası / Parapet Kapağı (Antrasit / Titanyum Çinko)
        p.fillRect(QRectF(bx - 3, by - 6, bw + 6, 6), QColor("#1e293b"))
        p.setPen(QPen(QColor("#0f172a"), 1))
        p.drawRect(QRectF(bx - 3, by - 6, bw + 6, 6))

        # Kat adetlerini ve kat yüksekliklerini belirle
        store_h = min(bh * 0.44, 3.8 * self.ppm)
        upper_h = (bh - store_h) / 2.0  # 2 üst kat

        # Kat Döşemeleri / Kat Silmeleri (Architectural String Courses)
        floor1_y = by + upper_h
        store_top_y = by + bh - store_h

        p.fillRect(QRectF(bx, floor1_y - 2, bw, 4), QColor("#cbd5e1"))
        p.setPen(QPen(QColor("#94a3b8"), 1.2))
        p.drawLine(QPointF(bx, floor1_y + 2), QPointF(bx + bw, floor1_y + 2))

        p.fillRect(QRectF(bx, store_top_y - 2, bw, 4), QColor("#94a3b8"))
        p.setPen(QPen(QColor("#64748b"), 1.2))
        p.drawLine(QPointF(bx, store_top_y + 2), QPointF(bx + bw, store_top_y + 2))

        # -------------------------------------------------------------
        # 3. ZEMİN KAT: ÇAĞDAŞ ŞEFFAF CAM VİTRİN VE TİCARİ MEKAN
        # -------------------------------------------------------------
        if bldg.ground_floor_commercial:
            store_rect = QRectF(bx + 4, store_top_y + 4, bw - 8, store_h - 6)

            # İç mekan sıcak amber aydınlatma gradyanı
            warm_grad = QLinearGradient(store_rect.topLeft(), store_rect.bottomLeft())
            warm_grad.setColorAt(0.0, QColor(254, 243, 199, 210))
            warm_grad.setColorAt(1.0, QColor(253, 230, 138, 140))
            p.fillRect(store_rect, warm_grad)

            # İç mekan silüetleri (Sarkıt lambalar, vitrin rafları)
            p.setPen(QPen(QColor("#78716c"), 1.0))
            for lx in (bx + bw * 0.32, bx + bw * 0.68):
                p.drawLine(QPointF(lx, store_top_y + 4), QPointF(lx, store_top_y + 16))
                p.fillRect(QRectF(lx - 4, store_top_y + 16, 8, 4), QColor("#1e293b"))
                p.fillRect(QRectF(lx - 3, store_top_y + 20, 6, 2), QColor("#f59e0b"))

            # Siyah alüminyum vitrin doğraması
            p.setPen(QPen(QColor("#0f172a"), 1.8))
            p.setBrush(BRUSH_STYLE_NOBRUSH)
            p.drawRect(store_rect)
            p.drawLine(QPointF(bx + bw * 0.52, store_top_y + 4), QPointF(bx + bw * 0.52, store_top_y + store_h - 2))

            # Cam yansıma çizgisi
            p.setPen(QPen(QColor(255, 255, 255, 120), 1.5))
            p.drawLine(QPointF(bx + 10, store_top_y + store_h - 8), QPointF(bx + bw * 0.44, store_top_y + 10))

            # Şık Antrasit Tabela Bandı (Fascia)
            sign_h = max(14.0, min(20.0, store_h * 0.22))
            sign_y = store_top_y - sign_h - 1
            p.fillRect(QRectF(bx + 2, sign_y, bw - 4, sign_h), QColor("#0f172a"))
            p.setPen(QPen(QColor("#334155"), 1))
            p.drawRect(QRectF(bx + 2, sign_y, bw - 4, sign_h))

            f_sign = QFont("Segoe UI", 6)
            f_sign.setBold(True)
            p.setFont(f_sign)
            p.setPen(QPen(QColor("#f8fafc"), 1))
            lang = getattr(self.section, "language", get_language())
            s_name = bldg.shop_name or (
                tr_text("canvas_shop_left", lang) if is_left else tr_text("canvas_shop_right", lang)
            )
            p.drawText(QRectF(bx + 2, sign_y, bw - 4, sign_h), ALIGN_CENTER, s_name)

            # Modern Mimari Tente / Saçak (Çelik Gergili)
            p.setBrush(QBrush(QColor(bldg.accent_color if bldg.accent_color else "#1e3a8a")))
            p.setPen(QPen(QColor("#0f172a"), 1.2))
            aw_y = sign_y + sign_h + 1
            aw_depth = min(20.0, bw * 0.32)
            if is_left:
                p.drawPolygon([
                    QPointF(bx + bw - 2, aw_y),
                    QPointF(bx + bw + aw_depth, aw_y + 6),
                    QPointF(bx + bw + aw_depth - 4, aw_y + 14),
                    QPointF(bx + bw - 2, aw_y + 10),
                ])
            else:
                p.drawPolygon([
                    QPointF(bx + 2, aw_y),
                    QPointF(bx - aw_depth, aw_y + 6),
                    QPointF(bx - aw_depth + 4, aw_y + 14),
                    QPointF(bx + 2, aw_y + 10),
                ])

            # Kaldırım Kafe Masası Tefrişi
            p.setPen(QPen(QColor("#1e293b"), 1.2))
            cx_table = (bx + bw + 14) if is_left else (bx - 14)
            p.drawLine(QPointF(cx_table - 6, rect.bottom() - 11), QPointF(cx_table + 6, rect.bottom() - 11))
            p.drawLine(QPointF(cx_table, rect.bottom() - 11), QPointF(cx_table, rect.bottom()))
            p.drawLine(QPointF(cx_table - 9, rect.bottom() - 8), QPointF(cx_table - 5, rect.bottom() - 8))
            p.drawLine(QPointF(cx_table - 7, rect.bottom() - 8), QPointF(cx_table - 7, rect.bottom()))

        # -------------------------------------------------------------
        # 4. ÜST KATLAR: MİMARİ PENCERELER, DENİZLİKLER VE BALKON
        # -------------------------------------------------------------
        win_w = max(24.0, bw * 0.38)
        win_h = max(28.0, upper_h * 0.58)

        for f_idx, fy_start in enumerate((by + 10, floor1_y + 8)):
            wx = bx + (bw - win_w) / 2
            wy = fy_start + (upper_h - win_h) / 2 - 2
            win_rect = QRectF(wx, wy, win_w, win_h)

            p.fillRect(win_rect, QColor("#e0f2fe"))
            p.setPen(QPen(QColor("#475569"), 1.2))
            p.drawRect(win_rect)

            # Cam yansıma çizgisi
            p.setPen(QPen(QColor(255, 255, 255, 140), 1.2))
            p.drawLine(QPointF(wx + 4, wy + win_h - 6), QPointF(wx + win_w - 6, wy + 4))

            # Pencere kayıtları
            p.setPen(QPen(QColor("#334155"), 1.0))
            p.drawLine(QPointF(wx + win_w / 2, wy), QPointF(wx + win_w / 2, wy + win_h))
            p.drawLine(QPointF(wx, wy + win_h * 0.36), QPointF(wx + win_w, wy + win_h * 0.36))

            # Mermer Denizlik (Sill)
            p.fillRect(QRectF(wx - 2, wy + win_h, win_w + 4, 3), QColor("#cbd5e1"))
            p.setPen(QPen(QColor("#94a3b8"), 0.8))
            p.drawRect(QRectF(wx - 2, wy + win_h, win_w + 4, 3))

            # Modern Fransız Balkon Korkuluğu (Siyah dikey demir parmaklık)
            railing_h = win_h * 0.38
            ry = wy + win_h - railing_h
            p.fillRect(QRectF(wx - 1, ry, win_w + 2, railing_h), QColor(15, 23, 42, 25))
            p.setPen(QPen(QColor("#0f172a"), 1.0))
            p.drawLine(QPointF(wx - 1, ry), QPointF(wx + win_w + 1, ry))
            for rx_bar in range(int(wx + 3), int(wx + win_w), 5):
                p.drawLine(QPointF(rx_bar, ry), QPointF(rx_bar, wy + win_h))

        p.restore()

    def _draw_road_segments(self, p, sec, x_road, y_ground):
        """Yol katmanları, asfalt, granit parke, bordür ve seçilebilir yeraltı altyapı boru şebekesi."""
        p.save()
        cur_x = x_road
        self._element_rects.clear()
        self._utility_rects.clear()

        show_subgrade = getattr(sec, "show_subgrade", True)
        show_utilities = getattr(sec, "show_utilities", True)
        show_slopes = getattr(sec, "show_slope_arrows", True)
        theme = getattr(sec, "visual_theme", "architectural")
        total_road_px = sec.total_width * self.ppm
        road_mid_x = x_road + total_road_px / 2.0

        for i, elem in enumerate(sec.elements):
            ew = elem.width * self.ppm
            eh = elem.elevation * self.ppm
            ey = y_ground - eh

            click_rect = QRectF(cur_x, 20, ew, y_ground + (80 if show_subgrade else 20))
            self._element_rects.append(click_rect)

            # 1. Aşınma Tabakası / Kaplama Yüzeyi
            if theme == "technical_cad":
                col = QColor("#e2e8f0") if elem.element_type == ElementType.SIDEWALK else QColor("#64748b")
            else:
                col = QColor(elem.surface_color)

            if i == self.selected_element_idx:
                col = col.lighter(116)
            elif i == self.hovered_element_idx:
                col = col.lighter(108)

            p.setBrush(QBrush(col))
            p.setPen(QPen(QColor("#334155"), 1))
            p.drawRect(QRectF(cur_x, ey, ew, 14 + eh))

            # Kaldırım Doğal Granit Parke Taşları (Staggered joints)
            if elem.element_type == ElementType.SIDEWALK:
                p.setPen(QPen(QColor("#cbd5e1"), 0.7))
                for px in range(int(cur_x + 8), int(cur_x + ew), 8):
                    p.drawLine(QPointF(px, ey), QPointF(px, ey + 14 + eh))

            # Granit Pahlı Bordür (Yoldan 15cm yüksek)
            if elem.has_curb:
                curb_w = min(7.0, max(4.0, ew * 0.08))
                p.fillRect(QRectF(cur_x + ew - curb_w, ey, curb_w, eh + 6), QColor("#94a3b8"))
                p.setPen(QPen(QColor("#475569"), 1))
                p.drawRect(QRectF(cur_x + ew - curb_w, ey, curb_w, eh + 6))
                p.setPen(QPen(QColor("#f8fafc"), 0.8))
                p.drawLine(QPointF(cur_x + ew - curb_w + 1, ey + 1), QPointF(cur_x + ew - 1, ey + 1))

            # Sarı Engelli İzi (Kabartmalı Takip & Uyarı Yüzeyi)
            if elem.has_tactile:
                tact_col = QColor("#cbd5e1") if theme == "technical_cad" else QColor("#facc15")
                p.fillRect(QRectF(cur_x + 10, ey + 1, min(16.0, ew - 12), 3.5), tact_col)
                p.setPen(QPen(QColor("#ca8a04"), 0.6))
                for tx in range(int(cur_x + 12), int(cur_x + min(16.0, ew - 12) + 8), 3):
                    p.drawLine(QPointF(tx, ey + 1), QPointF(tx, ey + 4.5))

            # Bisiklet Yolu Yeşil/Mavi Zemin & Beyaz Şablon
            if elem.element_type == ElementType.BIKE_LANE:
                bx = cur_x + ew / 2
                by = ey + 7
                p.setPen(QPen(QColor("#ffffff"), 1.8))
                p.setBrush(BRUSH_STYLE_NOBRUSH)
                p.drawEllipse(QPointF(bx - 8, by), 3.8, 3.8)
                p.drawEllipse(QPointF(bx + 8, by), 3.8, 3.8)
                p.drawLine(QPointF(bx - 8, by), QPointF(bx, by - 4))
                p.drawLine(QPointF(bx, by - 4), QPointF(bx + 8, by))

            # Araç Şeritleri Yön Okları (Beyaz Termoplastik Boya)
            if elem.element_type == ElementType.VEHICLE_LANE:
                arrow_x = cur_x + ew / 2
                arrow_y = ey + 7
                p.setPen(QPen(QColor("#ffffff"), 1.8))
                p.drawLine(QPointF(arrow_x, arrow_y + 4), QPointF(arrow_x, arrow_y - 4))
                p.drawLine(QPointF(arrow_x - 3, arrow_y - 1), QPointF(arrow_x, arrow_y - 4))
                p.drawLine(QPointF(arrow_x + 3, arrow_y - 1), QPointF(arrow_x, arrow_y - 4))

            # 2.0% Transverse Drainage Cross-Slope Arrows (Optional)
            if show_slopes and ew >= 38.0:
                f_slp = QFont("Arial", 5)
                f_slp.setBold(True)
                p.setFont(f_slp)
                mid_seg_x = cur_x + ew / 2.0
                is_tr = (normalize_lang(getattr(sec, "language", get_language())) == "tr")
                pct2 = "%2.0" if is_tr else "2.0%"
                pct15 = "%1.5" if is_tr else "1.5%"
                if elem.element_type in (ElementType.VEHICLE_LANE, ElementType.BUS_LANE, ElementType.PARKING):
                    slp_txt = f"← {pct2}" if mid_seg_x < road_mid_x else f"{pct2} →"
                    p.setPen(QPen(QColor("#fde047") if theme != "technical_cad" else QColor("#f8fafc"), 1))
                    p.drawText(QRectF(cur_x + 2, ey + 1, ew - 4, 8), ALIGN_RIGHT if mid_seg_x >= road_mid_x else ALIGN_LEFT, slp_txt)
                elif elem.element_type == ElementType.SIDEWALK:
                    slp_txt = f"{pct15} →" if mid_seg_x < road_mid_x else f"← {pct15}"
                    p.setPen(QPen(QColor("#475569"), 1))
                    p.drawText(QRectF(cur_x + 2, ey + 5, ew - 4, 8), ALIGN_CENTER, slp_txt)

            # Şerit Çizgileri
            if elem.marking == "dashed_white":
                pen = QPen(QColor("#ffffff"), 2.2)
                pen.setStyle(PEN_STYLE_DASHLINE)
                p.setPen(pen)
                p.drawLine(QPointF(cur_x + ew, ey - 1), QPointF(cur_x + ew, ey + 1))
            elif elem.marking == "solid_white":
                p.setPen(QPen(QColor("#ffffff"), 2.2))
                p.drawLine(QPointF(cur_x + ew, ey - 1), QPointF(cur_x + ew, ey + 1))

            # SEÇİLİ ŞERİT MAVİ VURGU ÇERÇEVESİ
            if i == self.selected_element_idx:
                p.setPen(QPen(QColor("#2563eb"), 2.5))
                p.setBrush(BRUSH_STYLE_NOBRUSH)
                p.drawRect(QRectF(cur_x + 1, ey - 2, ew - 2, 18 + eh))

            # -------------------------------------------------------------
            # 2. MÜHENDİSLİK ALTYAPI VE ZEMİN KATMANLARI (Yol Gövdesi Kesiti)
            # -------------------------------------------------------------
            if show_subgrade:
                # Aşınma altı: Asfalt Binder Tabakası (6 cm)
                p.fillRect(QRectF(cur_x, y_ground + 14, ew, 12), QColor("#334155"))
                # Plentmiks Temel (PMT - 15 cm)
                p.fillRect(QRectF(cur_x, y_ground + 26, ew, 16), QColor("#475569"))
                p.setPen(QPen(QColor("#64748b"), 0.5))
                for px in range(int(cur_x), int(cur_x + ew), 6):
                    p.drawLine(QPointF(px, y_ground + 26), QPointF(px + 4, y_ground + 42))

                # Kırmataş Alt Temel (PMAT - 20 cm)
                p.fillRect(QRectF(cur_x, y_ground + 42, ew, 18), QColor("#64748b"))

                # Sıkıştırılmış Doğal Zemin / Jeoteknik Dolgu Taraması (45 derece)
                p.fillRect(QRectF(cur_x, y_ground + 60, ew, 24), QColor("#d6d3d1"))
                p.setPen(QPen(QColor("#78716c"), 0.5))
                for hx in range(int(cur_x) - 10, int(cur_x + ew) + 10, 8):
                    p.drawLine(QPointF(hx, y_ground + 60), QPointF(hx + 8, y_ground + 84))

            cur_x += ew

        # Zemin alt çizgisi
        sub_bottom_y = (y_ground + 84) if show_subgrade else (y_ground + 14)
        p.setPen(QPen(QColor("#1e293b") if theme != "night_lighting" else QColor("#94a3b8"), 2))
        p.drawLine(QPointF(x_road - 40, sub_bottom_y), QPointF(x_road + total_road_px + 40, sub_bottom_y))

        # 3. Selectable Underground Utility Conduits & Gallery
        if show_subgrade and show_utilities:
            lang = getattr(sec, "language", get_language())
            pipe_y = y_ground + 51.0
            f_pipe = QFont("Arial", 5)
            f_pipe.setBold(True)
            p.setFont(f_pipe)

            if getattr(sec, "has_utility_gallery", False):
                gal_x = x_road + min(18.0, total_road_px * 0.05)
                gal_y = y_ground + 34.0
                gal_w = 66.0
                gal_h = 24.0
                gal_rect = QRectF(gal_x, gal_y, gal_w, gal_h)
                self._utility_rects["gallery"] = (gal_rect.adjusted(-3, -3, 3, 10), tr_text("pipe_gallery_tip", lang))

                p.fillRect(gal_rect, QColor("#cbd5e1"))
                p.setPen(QPen(QColor("#0f172a"), 1.4))
                p.drawRect(gal_rect)
                p.fillRect(gal_rect.adjusted(3, 3, -3, -3), QColor("#1e293b"))

                p.fillRect(QRectF(gal_x + 4, gal_y + 10, 12, 2), QColor("#94a3b8"))
                p.fillRect(QRectF(gal_x + 4, gal_y + 17, 12, 2), QColor("#94a3b8"))
                p.setBrush(QBrush(QColor("#38bdf8")))
                p.setPen(PEN_STYLE_NOPEN)
                p.drawEllipse(QPointF(gal_x + 24, gal_y + 15), 5.0, 5.0)
                p.setBrush(QBrush(QColor("#ef4444")))
                p.drawEllipse(QPointF(gal_x + 40, gal_y + 10), 3.5, 3.5)
                p.setBrush(QBrush(QColor("#f97316")))
                p.drawEllipse(QPointF(gal_x + 52, gal_y + 15), 4.0, 4.0)

                p.setPen(QPen(QColor("#1e293b"), 1))
                p.drawText(QRectF(gal_x - 4, gal_y + gal_h + 1, gal_w + 8, 9), ALIGN_CENTER, tr_text("pipe_gallery_short", lang))
            else:
                pipe_w_x = x_road + min(30.0, total_road_px * 0.08)
                if getattr(sec, "has_water_pipe", True):
                    p.setBrush(QBrush(QColor("#0284c7")))
                    p.setPen(QPen(QColor("#0f172a"), 1.2))
                    p.drawEllipse(QPointF(pipe_w_x, pipe_y), 7.5, 7.5)
                    p.setBrush(QBrush(QColor("#38bdf8")))
                    p.drawEllipse(QPointF(pipe_w_x, pipe_y), 5.2, 5.2)
                    p.setPen(QPen(QColor("#1e293b"), 1))
                    p.drawText(QRectF(pipe_w_x - 16, pipe_y + 8, 32, 9), ALIGN_CENTER, tr_text("pipe_water_short", lang))
                    self._utility_rects["water"] = (QRectF(pipe_w_x - 12, pipe_y - 10, 24, 26), tr_text("pipe_water_tip", lang))

                pipe_t_x = pipe_w_x + 28.0
                if getattr(sec, "has_telecom_pipe", True):
                    p.setBrush(QBrush(QColor("#dc2626")))
                    p.setPen(QPen(QColor("#0f172a"), 1.0))
                    p.drawEllipse(QPointF(pipe_t_x, pipe_y), 5.5, 5.5)
                    p.setBrush(QBrush(QColor("#fca5a5")))
                    p.drawEllipse(QPointF(pipe_t_x, pipe_y), 2.5, 2.5)
                    p.setPen(QPen(QColor("#1e293b"), 1))
                    p.drawText(QRectF(pipe_t_x - 14, pipe_y + 8, 28, 9), ALIGN_CENTER, tr_text("pipe_telecom_short", lang))
                    self._utility_rects["telecom"] = (QRectF(pipe_t_x - 11, pipe_y - 10, 22, 26), tr_text("pipe_telecom_tip", lang))

                pipe_e_x = pipe_t_x + 26.0
                if getattr(sec, "has_power_cable", True):
                    p.setBrush(QBrush(QColor("#ea580c")))
                    p.setPen(QPen(QColor("#0f172a"), 1.0))
                    p.drawEllipse(QPointF(pipe_e_x, pipe_y), 6.0, 6.0)
                    p.setBrush(QBrush(QColor("#fdba74")))
                    p.drawEllipse(QPointF(pipe_e_x, pipe_y), 3.0, 3.0)
                    p.setPen(QPen(QColor("#1e293b"), 1))
                    p.drawText(QRectF(pipe_e_x - 14, pipe_y + 8, 28, 9), ALIGN_CENTER, tr_text("pipe_power_short", lang))
                    self._utility_rects["power"] = (QRectF(pipe_e_x - 11, pipe_y - 10, 22, 26), tr_text("pipe_power_tip", lang))

            if getattr(sec, "has_sewer_pipe", False):
                sewer_x = x_road + total_road_px * 0.50
                sewer_y = y_ground + 50.0
                p.setBrush(QBrush(QColor("#78716c")))
                p.setPen(QPen(QColor("#0f172a"), 1.3))
                p.drawEllipse(QPointF(sewer_x, sewer_y), 11.5, 11.5)
                p.setBrush(QBrush(QColor("#292524")))
                p.drawEllipse(QPointF(sewer_x, sewer_y), 8.2, 8.2)
                p.fillRect(QRectF(sewer_x - 6, sewer_y + 2, 12, 4), QColor("#92400e"))
                p.setPen(QPen(QColor("#1e293b"), 1))
                p.drawText(QRectF(sewer_x - 24, sewer_y + 11, 48, 9), ALIGN_CENTER, tr_text("pipe_sewer_short", lang))
                self._utility_rects["sewer"] = (QRectF(sewer_x - 16, sewer_y - 13, 32, 32), tr_text("pipe_sewer_tip", lang))

            pipe_d_x = x_road + total_road_px - min(38.0, total_road_px * 0.10)
            if getattr(sec, "has_drainage_pipe", True):
                p.setBrush(QBrush(QColor("#15803d")))
                p.setPen(QPen(QColor("#0f172a"), 1.2))
                p.drawEllipse(QPointF(pipe_d_x, pipe_y), 10.0, 10.0)
                p.setBrush(QBrush(QColor("#1e293b")))
                p.drawEllipse(QPointF(pipe_d_x, pipe_y), 7.2, 7.2)
                p.setPen(QPen(QColor("#1e293b"), 1))
                p.drawText(QRectF(pipe_d_x - 22, pipe_y + 9, 44, 9), ALIGN_CENTER, tr_text("pipe_drainage_short", lang))
                self._utility_rects["drainage"] = (QRectF(pipe_d_x - 15, pipe_y - 12, 30, 30), tr_text("pipe_drainage_tip", lang))

            pipe_g_x = pipe_d_x - 32.0
            if getattr(sec, "has_gas_pipe", True):
                p.setBrush(QBrush(QColor("#eab308")))
                p.setPen(QPen(QColor("#0f172a"), 1.0))
                p.drawEllipse(QPointF(pipe_g_x, pipe_y), 5.5, 5.5)
                p.setBrush(QBrush(QColor("#fef08a")))
                p.drawEllipse(QPointF(pipe_g_x, pipe_y), 2.8, 2.8)
                p.setPen(QPen(QColor("#1e293b"), 1))
                p.drawText(QRectF(pipe_g_x - 16, pipe_y + 8, 32, 9), ALIGN_CENTER, tr_text("pipe_gas_short", lang))
                self._utility_rects["gas"] = (QRectF(pipe_g_x - 12, pipe_y - 10, 24, 26), tr_text("pipe_gas_tip", lang))

            if self.hovered_utility_key and self.hovered_utility_key in self._utility_rects:
                u_rect, u_lbl = self._utility_rects[self.hovered_utility_key]
                p.setPen(QPen(QColor("#ef4444"), 2.0, PEN_STYLE_DASHLINE))
                p.setBrush(QBrush(QColor(239, 68, 68, 35)))
                p.drawRoundedRect(u_rect, 4, 4)

                tip_w = 165.0
                tip_h = 18.0
                tip_x = max(10.0, min(float(self.width() - tip_w - 10), u_rect.center().x() - tip_w / 2))
                tip_y = u_rect.top() - tip_h - 4
                p.fillRect(QRectF(tip_x, tip_y, tip_w, tip_h), QColor("#0f172a"))
                p.setPen(QPen(QColor("#f87171"), 1.2))
                p.drawRoundedRect(QRectF(tip_x, tip_y, tip_w, tip_h), 4, 4)
                f_tip = QFont("Arial", 6)
                f_tip.setBold(True)
                p.setFont(f_tip)
                p.setPen(QPen(QColor("#ffffff"), 1))
                p.drawText(QRectF(tip_x, tip_y, tip_w, tip_h), ALIGN_CENTER, tr_text("pipe_click_remove", lang, label=u_lbl))

        p.restore()

    def _draw_furniture_and_trees(self, p, sec, x_road, y_ground):
        p.save()
        cur_x = x_road
        theme = getattr(sec, "visual_theme", "architectural")

        for elem in sec.elements:
            ew = elem.width * self.ppm
            mid_x = cur_x + ew / 2
            base_y = y_ground - (elem.elevation * self.ppm)

            # -------------------------------------------------------------
            # 1. GERÇEKÇİ ORGANİK MİMARİ AĞAÇ (Botanical Branching & Layered Canopy)
            # -------------------------------------------------------------
            if elem.has_trees:
                th = max(55.0, 2.7 * self.ppm)   # Gövde yüksekliği (~2.7m)
                tr = max(42.0, 2.1 * self.ppm)   # Taç yarıçapı (~2.1m)

                # A) Ağacın zemine düşen yumuşak mimari gölgesi (Asfalt/Kaldırım üzerinde)
                p.setBrush(QBrush(QColor(15, 23, 42, 40)))
                p.setPen(PEN_STYLE_NOPEN)
                p.drawEllipse(QPointF(mid_x + 6, base_y + 1), tr * 0.9, 5.0)

                # B) Döküm Ağaç Kök Izgarası (Cast Iron Tree Grate)
                grate_w = max(26.0, 1.4 * self.ppm)
                p.fillRect(QRectF(mid_x - grate_w / 2, base_y - 2, grate_w, 4), QColor("#1e293b"))
                p.setPen(QPen(QColor("#475569"), 0.8))
                for gx in range(int(mid_x - grate_w / 2 + 3), int(mid_x + grate_w / 2), 4):
                    p.drawLine(QPointF(gx, base_y - 2), QPointF(gx, base_y + 2))

                # C) Odunsu Doğal Gövde ve Dallanma Sistemi (Trunk & Structural Limbs)
                trunk_col = QColor("#475569") if theme == "technical_cad" else QColor("#573016")
                trunk_pen = QColor("#1e293b") if theme == "technical_cad" else QColor("#381e0b")
                p.setBrush(QBrush(trunk_col))
                p.setPen(QPen(trunk_pen, 1.2))

                split_y = base_y - th * 0.70
                p.drawPolygon([
                    QPointF(mid_x - 4.5, base_y - 2),
                    QPointF(mid_x - 2.5, split_y),
                    QPointF(mid_x - 14.0, base_y - th),
                    QPointF(mid_x - 11.0, base_y - th - 3),
                    QPointF(mid_x - 1.0, split_y + 6),
                    QPointF(mid_x, base_y - th - 8),
                    QPointF(mid_x + 2.0, base_y - th - 8),
                    QPointF(mid_x + 1.0, split_y + 6),
                    QPointF(mid_x + 11.0, base_y - th - 3),
                    QPointF(mid_x + 14.0, base_y - th),
                    QPointF(mid_x + 2.5, split_y),
                    QPointF(mid_x + 4.5, base_y - 2),
                ])

                # D) Çok Katmanlı Organik Taç Kümesi (Layered Foliage Lobes)
                cy = base_y - th - tr * 0.65

                if theme == "technical_cad":
                    foliage_lobes = [
                        (0.0, 0.0, tr * 0.78, QColor(203, 213, 225, 190)),
                        (-tr * 0.45, tr * 0.15, tr * 0.55, QColor(226, 232, 240, 200)),
                        (tr * 0.45, tr * 0.15, tr * 0.55, QColor(226, 232, 240, 200)),
                        (-tr * 0.38, -tr * 0.35, tr * 0.58, QColor(241, 245, 249, 210)),
                        (tr * 0.38, -tr * 0.35, tr * 0.58, QColor(241, 245, 249, 210)),
                        (0.0, -tr * 0.50, tr * 0.62, QColor(248, 250, 252, 220)),
                    ]
                    p.setPen(QPen(QColor("#334155"), 1.0))
                    for dx, dy, rad, col in foliage_lobes:
                        p.setBrush(QBrush(col))
                        p.drawEllipse(QPointF(mid_x + dx, cy + dy), rad, rad * 0.95)
                else:
                    foliage_lobes = [
                        (0.0, 0.0, tr * 0.78, QColor("#14532d")),
                        (-tr * 0.45, tr * 0.15, tr * 0.55, QColor("#166534")),
                        (tr * 0.45, tr * 0.15, tr * 0.55, QColor("#166534")),
                        (-tr * 0.38, -tr * 0.35, tr * 0.58, QColor("#15803d")),
                        (tr * 0.38, -tr * 0.35, tr * 0.58, QColor("#15803d")),
                        (0.0, -tr * 0.50, tr * 0.62, QColor("#16a34a")),
                        (-tr * 0.20, -tr * 0.10, tr * 0.68, QColor("#15803d")),
                        (tr * 0.20, -tr * 0.10, tr * 0.68, QColor("#22c55e")),
                        (tr * 0.10, -tr * 0.30, tr * 0.50, QColor("#4ade80")),
                    ]
                    p.setPen(PEN_STYLE_NOPEN)
                    for dx, dy, rad, col in foliage_lobes:
                        rad_g = QRadialGradient(mid_x + dx - rad * 0.3, cy + dy - rad * 0.3, rad)
                        rad_g.setColorAt(0.0, col.lighter(125))
                        rad_g.setColorAt(0.7, col)
                        rad_g.setColorAt(1.0, col.darker(130))
                        p.setBrush(QBrush(rad_g))
                        p.drawEllipse(QPointF(mid_x + dx, cy + dy), rad, rad * 0.95)

                    # E) Doğal Yaprak Dokusu (Çevresel minik yaprak dalgaları)
                    p.setPen(QPen(QColor("#14532d"), 0.8))
                    for ang_i in range(16):
                        ang = ang_i * (2.0 * math.pi / 16.0)
                        r_scallop = tr * (0.88 + 0.10 * math.sin(ang_i * 2.3))
                        sx = mid_x + r_scallop * math.cos(ang)
                        sy = cy + r_scallop * math.sin(ang) * 0.95
                        p.setBrush(QBrush(QColor("#16a34a")))
                        p.drawEllipse(QPointF(sx, sy), 5.5, 5.0)

            # -------------------------------------------------------------
            # 2. ÇAĞDAŞ LED AYDINLATMA DİREĞİ VE YUMUŞAK IŞIK KONİSİ
            # -------------------------------------------------------------
            if elem.has_lighting:
                ph = 4.3 * self.ppm
                pole_x = cur_x + min(14.0, ew * 0.2)

                cone_alpha_top = 155 if theme == "night_lighting" else (25 if theme == "technical_cad" else 75)
                cone_alpha_mid = 85 if theme == "night_lighting" else (10 if theme == "technical_cad" else 32)
                cone_grad = QLinearGradient(pole_x + 18, base_y - ph, pole_x + 18, base_y)
                cone_grad.setColorAt(0.0, QColor(254, 240, 138, cone_alpha_top))
                cone_grad.setColorAt(0.6, QColor(254, 240, 138, cone_alpha_mid))
                cone_grad.setColorAt(1.0, QColor(254, 240, 138, 0))
                p.setBrush(QBrush(cone_grad))
                p.setPen(PEN_STYLE_NOPEN)
                p.drawPolygon([
                    QPointF(pole_x + 18, base_y - ph + 4),
                    QPointF(pole_x - 24, base_y),
                    QPointF(pole_x + 60, base_y),
                ])

                p.setPen(QPen(QColor("#cbd5e1") if theme == "night_lighting" else QColor("#0f172a"), 2.2))
                p.drawLine(QPointF(pole_x, base_y), QPointF(pole_x, base_y - ph + 8))
                p.drawLine(QPointF(pole_x, base_y - ph + 8), QPointF(pole_x + 6, base_y - ph))
                p.drawLine(QPointF(pole_x + 6, base_y - ph), QPointF(pole_x + 22, base_y - ph - 2))
                p.fillRect(QRectF(pole_x + 12, base_y - ph - 1, 14, 3.5), QColor("#1e293b"))
                p.fillRect(QRectF(pole_x + 14, base_y - ph + 2.5, 10, 1.5), QColor("#fde047"))

            # -------------------------------------------------------------
            # 3. MİMARİ AHŞAP ÇITALI PARKE BANKI
            # -------------------------------------------------------------
            if elem.has_bench:
                bx = mid_x - 14
                p.fillRect(QRectF(bx, base_y - 13, 28, 2.5), QColor("#92400e"))
                p.fillRect(QRectF(bx, base_y - 7, 28, 2.5), QColor("#92400e"))
                p.setPen(QPen(QColor("#0f172a"), 1.8))
                p.drawLine(QPointF(bx + 4, base_y), QPointF(bx + 4, base_y - 13))
                p.drawLine(QPointF(bx + 24, base_y), QPointF(bx + 24, base_y - 13))
                p.drawLine(QPointF(bx + 3, base_y - 13), QPointF(bx + 1, base_y - 20))
                p.fillRect(QRectF(bx - 1, base_y - 21, 28, 2.5), QColor("#92400e"))

            # -------------------------------------------------------------
            # 4. ÇAĞDAŞ CAM OTOBÜS DURAĞI KABİNİ
            # -------------------------------------------------------------
            if elem.has_bus_shelter:
                sh_w = min(46.0, ew - 4)
                sh_h = 2.4 * self.ppm
                sh_x = cur_x + ew - sh_w - 4

                p.fillRect(QRectF(sh_x - 3, base_y - sh_h - 3, sh_w + 6, 4), QColor("#0f172a"))
                p.fillRect(QRectF(sh_x - 2, base_y - sh_h, 4, sh_h), QColor("#0f172a"))
                p.fillRect(QRectF(sh_x + sh_w - 2, base_y - sh_h, 4, sh_h), QColor("#0f172a"))

                glass_rect = QRectF(sh_x + 2, base_y - sh_h + 1, sh_w - 4, sh_h - 2)
                p.fillRect(glass_rect, QColor(224, 242, 254, 160))
                p.setPen(QPen(QColor("#38bdf8"), 1.0))
                p.drawRect(glass_rect)

                p.setPen(QPen(QColor(255, 255, 255, 200), 1.0))
                for dot_x in range(int(sh_x + 8), int(sh_x + sh_w - 6), 8):
                    p.drawPoint(QPointF(dot_x, base_y - sh_h * 0.55))

                p.fillRect(QRectF(sh_x + 4, base_y - sh_h + 8, 12, sh_h * 0.45), QColor("#ffffff"))
                p.setPen(QPen(QColor("#ef4444"), 1))
                p.drawRect(QRectF(sh_x + 4, base_y - sh_h + 8, 12, sh_h * 0.45))
                p.fillRect(QRectF(sh_x + 18, base_y - 11, sh_w - 22, 2.5), QColor("#b45309"))

            cur_x += ew

        p.restore()

    def _draw_figures(self, p, sec, x_road, y_ground):
        p.save()
        cur_x = x_road

        for elem in sec.elements:
            ew = elem.width * self.ppm
            mid_x = cur_x + ew / 2
            base_y = y_ground - (elem.elevation * self.ppm)

            if elem.pedestrian_count > 0:
                p_offsets = [0] if elem.pedestrian_count == 1 else [-12, 12] if elem.pedestrian_count == 2 else [-18, 0, 18]
                for p_idx, p_off in enumerate(p_offsets):
                    self._draw_human(p, mid_x + p_off, base_y, variant=p_idx % 3)

            if elem.cyclist_count > 0:
                self._draw_cyclist(p, mid_x, base_y)

            if elem.vehicle_type == "car":
                self._draw_car(p, mid_x, base_y)
            elif elem.vehicle_type == "bus":
                self._draw_bus(p, mid_x, base_y)

            cur_x += ew

        p.restore()

    def _draw_human(self, p, x, y, variant=0):
        scale = self.ppm / 32.0
        h_tot = 1.75 * self.ppm

        p.save()
        p.setPen(PEN_STYLE_NOPEN)
        p.setBrush(QBrush(QColor("#1e293b")))

        if variant == 0:
            # 1. Çantalı yürüyen profesyonel
            head_r = 3.6 * scale
            head_y = y - h_tot + head_r
            p.drawEllipse(QPointF(x, head_y), head_r, head_r)

            p.drawPolygon([
                QPointF(x - 4.5 * scale, head_y + head_r + 2),
                QPointF(x + 4.5 * scale, head_y + head_r + 2),
                QPointF(x + 3.8 * scale, y - 22 * scale),
                QPointF(x + 5.5 * scale, y - 2 * scale),
                QPointF(x + 2.5 * scale, y),
                QPointF(x + 0.5 * scale, y - 20 * scale),
                QPointF(x - 3.5 * scale, y),
                QPointF(x - 6.0 * scale, y - 2 * scale),
                QPointF(x - 3.8 * scale, y - 22 * scale),
            ])
            p.fillRect(QRectF(x + 4.0 * scale, y - 28 * scale, 5.0 * scale, 7.0 * scale), QColor("#0f172a"))

        elif variant == 1:
            # 2. Paltolu yürüyen kadın silüeti
            head_r = 3.4 * scale
            head_y = y - h_tot + head_r
            p.drawEllipse(QPointF(x, head_y), head_r, head_r)

            p.drawPolygon([
                QPointF(x - 4.0 * scale, head_y + head_r + 2),
                QPointF(x + 4.0 * scale, head_y + head_r + 2),
                QPointF(x + 6.0 * scale, y - 14 * scale),
                QPointF(x + 3.0 * scale, y),
                QPointF(x + 1.0 * scale, y),
                QPointF(x, y - 12 * scale),
                QPointF(x - 1.0 * scale, y),
                QPointF(x - 3.0 * scale, y),
                QPointF(x - 6.0 * scale, y - 14 * scale),
            ])
            p.fillRect(QRectF(x - 7.0 * scale, y - 22 * scale, 4.0 * scale, 5.0 * scale), QColor("#475569"))

        else:
            # 3. Akıllı telefona bakan genç
            head_r = 3.5 * scale
            head_y = y - h_tot + head_r
            p.drawEllipse(QPointF(x, head_y), head_r, head_r)

            p.drawPolygon([
                QPointF(x - 4.0 * scale, head_y + head_r + 2),
                QPointF(x + 4.0 * scale, head_y + head_r + 2),
                QPointF(x + 3.5 * scale, y - 24 * scale),
                QPointF(x + 2.0 * scale, y),
                QPointF(x - 0.5 * scale, y),
                QPointF(x, y - 22 * scale),
                QPointF(x - 2.5 * scale, y),
                QPointF(x - 4.5 * scale, y),
                QPointF(x - 3.5 * scale, y - 24 * scale),
            ])
            p.fillRect(QRectF(x + 2.5 * scale, y - 32 * scale, 2.5 * scale, 4.5 * scale), QColor("#38bdf8"))

        p.restore()

    def _draw_cyclist(self, p, x, y):
        scale = self.ppm / 32.0
        p.save()

        # 1. Bisiklet Tekerlekleri
        r_wheel = 9.0 * scale
        p.setPen(QPen(QColor("#0f172a"), 1.8))
        p.setBrush(BRUSH_STYLE_NOBRUSH)
        p.drawEllipse(QPointF(x - 14 * scale, y - r_wheel), r_wheel, r_wheel)
        p.drawEllipse(QPointF(x + 14 * scale, y - r_wheel), r_wheel, r_wheel)
        p.setPen(QPen(QColor("#94a3b8"), 0.8))
        for rad_a in (0, 45, 90, 135):
            p.drawLine(QPointF(x - 14 * scale, y - r_wheel - 5 * scale), QPointF(x - 14 * scale, y - r_wheel + 5 * scale))
            p.drawLine(QPointF(x + 14 * scale, y - r_wheel - 5 * scale), QPointF(x + 14 * scale, y - r_wheel + 5 * scale))

        # 2. Modern Diamond Bisiklet Kadrosu
        p.setPen(QPen(QColor("#0284c7"), 2.2))
        bb_pt = QPointF(x, y - r_wheel)
        rear_hub = QPointF(x - 14 * scale, y - r_wheel)
        front_hub = QPointF(x + 14 * scale, y - r_wheel)
        seat_post = QPointF(x - 4 * scale, y - 24 * scale)
        head_tube = QPointF(x + 9 * scale, y - 24 * scale)

        p.drawLine(rear_hub, bb_pt)
        p.drawLine(bb_pt, seat_post)
        p.drawLine(seat_post, rear_hub)
        p.drawLine(bb_pt, head_tube)
        p.drawLine(seat_post, head_tube)
        p.drawLine(head_tube, front_hub)

        # Sele ve Gidon
        p.setPen(QPen(QColor("#0f172a"), 2.5))
        p.drawLine(QPointF(x - 8 * scale, y - 25 * scale), QPointF(x - 2 * scale, y - 25 * scale))
        p.drawLine(head_tube, QPointF(x + 9 * scale, y - 28 * scale))
        p.drawLine(QPointF(x + 7 * scale, y - 28 * scale), QPointF(x + 12 * scale, y - 28 * scale))

        # 3. Kasklı ve Sırt Çantalı Bisiklet Sürücüsü
        p.setBrush(QBrush(QColor("#1e293b")))
        p.setPen(PEN_STYLE_NOPEN)
        head_pt = QPointF(x + 4 * scale, y - 42 * scale)
        p.drawEllipse(head_pt, 4.2 * scale, 4.2 * scale)

        p.setPen(QPen(QColor("#1e293b"), 3.2))
        p.drawLine(head_pt, QPointF(x - 4 * scale, y - 24 * scale))
        p.drawLine(head_pt, QPointF(x + 9 * scale, y - 27 * scale))
        p.drawLine(QPointF(x - 4 * scale, y - 24 * scale), QPointF(x + 3 * scale, y - 14 * scale))
        p.drawLine(QPointF(x + 3 * scale, y - 14 * scale), bb_pt)
        p.fillRect(QRectF(x - 8 * scale, y - 38 * scale, 6 * scale, 10 * scale), QColor("#0369a1"))

        p.restore()

    def _draw_car(self, p, x, y):
        w = 1.86 * self.ppm
        h = 1.48 * self.ppm
        bx = x - w / 2
        by = y - h

        p.save()

        # 1. Asfalt Üzeri Kontak Gölgesi
        p.setBrush(QBrush(QColor(15, 23, 42, 130)))
        p.setPen(PEN_STYLE_NOPEN)
        p.drawRoundedRect(QRectF(bx - 2, y - 5, w + 4, 7), 3, 3)

        # 2. Arka Lastikler
        tire_w = w * 0.16
        p.fillRect(QRectF(bx + 3, y - 9, tire_w, 9), QColor("#0f172a"))
        p.fillRect(QRectF(bx + w - tire_w - 3, y - 9, tire_w, 9), QColor("#0f172a"))

        # 3. Gövde ve Tumblehome Kabin
        cab_w = w * 0.74
        cab_x = x - cab_w / 2
        cab_h = h * 0.48

        p.fillRect(QRectF(x - 1.5, by - 3, 3, 3), QColor("#1e293b"))

        p.setBrush(QBrush(QColor("#0284c7")))
        p.setPen(QPen(QColor("#0369a1"), 1.2))
        p.drawPolygon([
            QPointF(cab_x + 4, by),
            QPointF(cab_x + cab_w - 4, by),
            QPointF(bx + w - 2, by + cab_h),
            QPointF(bx + 2, by + cab_h),
        ])

        p.fillRect(QRectF(cab_x + 5, by + 3, cab_w - 10, cab_h - 5), QColor("#0f172a"))
        p.setPen(QPen(QColor(234, 88, 12, 160), 0.6))
        for ry in range(int(by + 8), int(by + cab_h - 4), 4):
            p.drawLine(QPointF(cab_x + 8, ry), QPointF(cab_x + cab_w - 8, ry))
        p.fillRect(QRectF(x - 5, by + 2, 10, 2), QColor("#ef4444"))

        # 4. Alt Gövde / Geniş Omuzlar
        p.setBrush(QBrush(QColor("#0284c7")))
        p.setPen(QPen(QColor("#0369a1"), 1.2))
        p.drawRoundedRect(QRectF(bx, by + cab_h - 2, w, h - cab_h - 2), 4, 4)

        # 5. Çağdaş LED Stop Işık Bandı
        light_y = by + cab_h + 3
        p.fillRect(QRectF(bx + 3, light_y, w - 6, 5), QColor("#991b1b"))
        p.fillRect(QRectF(bx + 4, light_y + 1, 12, 3), QColor("#ef4444"))
        p.fillRect(QRectF(bx + w - 16, light_y + 1, 12, 3), QColor("#ef4444"))
        p.fillRect(QRectF(bx + 18, light_y + 1, w - 36, 2), QColor("#fca5a5"))

        # 6. Bagaj Kapağı ve Türk Plakası
        plate_w = 26.0
        plate_h = 6.0
        plate_y = light_y + 9
        p.fillRect(QRectF(x - plate_w / 2, plate_y, plate_w, plate_h), QColor("#ffffff"))
        p.fillRect(QRectF(x - plate_w / 2, plate_y, 4, plate_h), QColor("#1d4ed8"))
        p.setPen(QPen(QColor("#0f172a"), 0.8))
        p.drawRect(QRectF(x - plate_w / 2, plate_y, plate_w, plate_h))
        f_plate = QFont("Arial", 4)
        f_plate.setBold(True)
        p.setFont(f_plate)
        p.drawText(QRectF(x - plate_w / 2 + 4, plate_y, plate_w - 4, plate_h), ALIGN_CENTER, "35 ARCH 26")

        # 7. Yan Dikiz Aynaları
        p.fillRect(QRectF(bx - 5, by + cab_h - 4, 5, 4), QColor("#0284c7"))
        p.fillRect(QRectF(bx + w, by + cab_h - 4, 5, 4), QColor("#0284c7"))

        p.restore()

    def _draw_bus(self, p, x, y):
        w = 2.55 * self.ppm
        h = 3.20 * self.ppm
        bx = x - w / 2
        by = y - h

        p.save()

        # 1. Asfalt Üzeri Gövde Altı Derin Gölge
        p.setBrush(QBrush(QColor(15, 23, 42, 140)))
        p.setPen(PEN_STYLE_NOPEN)
        p.drawRoundedRect(QRectF(bx - 2, y - 6, w + 4, 8), 3, 3)

        # 2. Kauçuk Şehir İçi Otobüs Lastikleri
        tire_w = w * 0.16
        tire_h = 13.0
        p.fillRect(QRectF(bx + 4, y - tire_h, tire_w, tire_h), QColor("#0f172a"))
        p.fillRect(QRectF(bx + w - tire_w - 4, y - tire_h, tire_w, tire_h), QColor("#0f172a"))
        p.fillRect(QRectF(bx + 6, y - tire_h + 3, tire_w - 4, tire_h - 6), QColor("#94a3b8"))
        p.fillRect(QRectF(bx + w - tire_w - 2, y - tire_h + 3, tire_w - 4, tire_h - 6), QColor("#94a3b8"))

        # 3. Tavan Klima Ünitesi (Rooftop HVAC Pod)
        hvac_w = w * 0.55
        hvac_h = 7.0
        p.fillRect(QRectF(x - hvac_w / 2, by - hvac_h, hvac_w, hvac_h + 2), QColor("#e2e8f0"))
        p.setPen(QPen(QColor("#64748b"), 1))
        p.drawRect(QRectF(x - hvac_w / 2, by - hvac_h, hvac_w, hvac_h + 2))
        for lx in range(int(x - hvac_w / 2 + 6), int(x + hvac_w / 2 - 4), 5):
            p.drawLine(QPointF(lx, by - hvac_h + 2), QPointF(lx, by - 1))

        # 4. Otobüs Ana Gövdesi (İzmir ESHOT Zümrüt Yeşili & Beyaz Çift Ton)
        p.setPen(QPen(QColor("#064e3b"), 1.5))
        p.setBrush(QBrush(QColor("#059669")))
        p.drawRoundedRect(QRectF(bx, by, w, h - 3), 7, 7)

        # Üst Beyaz Kuşak
        p.fillRect(QRectF(bx + 1, by + 1, w - 2, h * 0.22), QColor("#f8fafc"))
        p.fillRect(QRectF(bx + 1, by + h * 0.22 - 2, w - 2, 3), QColor("#0f172a"))

        # 5. Glowing Amber LED Güzergah Tabelası
        matrix_w = w * 0.76
        matrix_h = max(11.0, h * 0.12)
        matrix_y = by + 6
        p.fillRect(QRectF(x - matrix_w / 2, matrix_y, matrix_w, matrix_h), QColor("#0f172a"))
        p.setPen(QPen(QColor("#1e293b"), 1))
        p.drawRect(QRectF(x - matrix_w / 2, matrix_y, matrix_w, matrix_h))

        f_led = QFont("Consolas", 6)
        f_led.setBold(True)
        p.setFont(f_led)
        p.setPen(QPen(QColor("#f59e0b"), 1))
        lang = getattr(self.section, "language", get_language())
        p.drawText(QRectF(x - matrix_w / 2, matrix_y, matrix_w, matrix_h), ALIGN_CENTER, tr_text("canvas_bus_led", lang))

        # 6. Panoramik Karartmalı Ön Cam & Silecekler
        wind_y = matrix_y + matrix_h + 4
        wind_h = h * 0.44
        wind_w = w * 0.88
        wind_rect = QRectF(x - wind_w / 2, wind_y, wind_w, wind_h)

        p.fillRect(wind_rect, QColor("#0f172a"))
        p.fillRect(QRectF(x - wind_w / 2 + 2, wind_y + 2, wind_w - 4, wind_h - 4), QColor("#1e293b"))
        glass_grad = QLinearGradient(wind_rect.topLeft(), wind_rect.bottomRight())
        glass_grad.setColorAt(0.0, QColor(14, 165, 233, 140))
        glass_grad.setColorAt(1.0, QColor(2, 132, 199, 80))
        p.fillRect(QRectF(x - wind_w / 2 + 3, wind_y + 3, wind_w - 6, wind_h - 6), glass_grad)

        p.setPen(QPen(QColor("#0f172a"), 1.4))
        p.drawLine(QPointF(x - 12, wind_y + wind_h - 2), QPointF(x - 4, wind_y + wind_h - 14))
        p.drawLine(QPointF(x + 4, wind_y + wind_h - 2), QPointF(x + 12, wind_y + wind_h - 14))

        # 7. Ön Panjur ve Amblem
        grill_y = wind_y + wind_h + 6
        p.fillRect(QRectF(x - w * 0.25, grill_y, w * 0.50, 8), QColor("#0f172a"))
        p.fillRect(QRectF(x - 3, grill_y + 2, 6, 4), QColor("#cbd5e1"))

        # 8. LED Projektör Farlar
        p.fillRect(QRectF(bx + 4, grill_y - 2, 12, 8), QColor("#f8fafc"))
        p.fillRect(QRectF(bx + 6, grill_y, 8, 4), QColor("#fef08a"))
        p.fillRect(QRectF(bx + w - 16, grill_y - 2, 12, 8), QColor("#f8fafc"))
        p.fillRect(QRectF(bx + w - 14, grill_y, 8, 4), QColor("#fef08a"))

        # 9. Türk Standart Plakası
        plate_w = 32.0
        plate_h = 7.0
        plate_y = grill_y + 11
        p.fillRect(QRectF(x - plate_w / 2, plate_y, plate_w, plate_h), QColor("#ffffff"))
        p.fillRect(QRectF(x - plate_w / 2, plate_y, 5, plate_h), QColor("#1d4ed8"))
        p.setPen(QPen(QColor("#0f172a"), 0.8))
        p.drawRect(QRectF(x - plate_w / 2, plate_y, plate_w, plate_h))
        f_plate = QFont("Arial", 4)
        f_plate.setBold(True)
        p.setFont(f_plate)
        p.drawText(QRectF(x - plate_w / 2 + 5, plate_y, plate_w - 5, plate_h), ALIGN_CENTER, "35 ESHOT 26")

        # 10. Yan Dikiz Aynaları
        p.setPen(QPen(QColor("#0f172a"), 1.8))
        p.drawLine(QPointF(bx + 2, by + 12), QPointF(bx - 7, by + 18))
        p.fillRect(QRectF(bx - 10, by + 14, 4, 12), QColor("#0f172a"))
        p.drawLine(QPointF(bx + w - 2, by + 12), QPointF(bx + w + 7, by + 18))
        p.fillRect(QRectF(bx + w + 6, by + 14, 4, 12), QColor("#0f172a"))

        p.restore()

    def _draw_streetmix_cards(self, p, sec, x_road, y_ground):
        """Streetmix tarzı şerit üstü interaktif kontrol kartları ([-] [+] butonları ve etiket)."""
        p.save()
        cur_x = x_road
        self._btn_rects.clear()

        card_y = 22.0

        for i, elem in enumerate(sec.elements):
            ew = elem.width * self.ppm
            mid_x = cur_x + ew / 2
            is_selected = (i == self.selected_element_idx)
            is_hovered = (i == self.hovered_element_idx)

            card_w = max(48.0, min(ew - 3.0, 105.0))
            card_x = mid_x - card_w / 2
            card_h = 42.0

            # 1. Kart Arka Planı
            bg_col = QColor("#ffffff") if is_selected else QColor("#f8fafc")
            border_col = QColor("#2563eb") if is_selected else QColor("#cbd5e1") if not is_hovered else QColor("#60a5fa")
            p.setBrush(QBrush(bg_col))
            p.setPen(QPen(border_col, 2.0 if is_selected else 1.2))
            p.drawRoundedRect(QRectF(card_x, card_y, card_w, card_h), 5, 5)

            # Silme [x] butonu
            btn_del_size = 10.0
            btn_del_rect = QRectF(card_x + card_w - btn_del_size - 3, card_y + 3, btn_del_size, btn_del_size)
            self._btn_rects[(i, "delete")] = btn_del_rect
            is_del_hov = (self.hovered_action == (i, "delete"))
            p.setBrush(QBrush(QColor("#fee2e2") if is_del_hov else QColor("#f1f5f9")))
            p.setPen(QPen(QColor("#ef4444") if is_del_hov else QColor("#94a3b8"), 0.8))
            p.drawRoundedRect(btn_del_rect, 2, 2)
            f_del = QFont("Arial", 6)
            f_del.setBold(True)
            p.setFont(f_del)
            p.setPen(QPen(QColor("#dc2626") if is_del_hov else QColor("#64748b"), 1))
            p.drawText(btn_del_rect, ALIGN_CENTER, "x")

            # 2. Şerit Adı
            f_name = QFont("Arial", 7)
            f_name.setBold(True)
            p.setFont(f_name)
            p.setPen(QPen(QColor("#1e293b"), 1))
            lbl_short = elem.label
            max_chars = max(5, int(card_w / 7.0))
            if len(lbl_short) > max_chars:
                lbl_short = lbl_short[:max_chars - 2] + ".."
            p.drawText(QRectF(card_x + 3, card_y + 3, card_w - btn_del_size - 6, 13), ALIGN_LEFT, lbl_short)

            # 3. [-] Genişlik [+] Butonları
            btn_size = 14.0
            btn_minus_rect = QRectF(card_x + 3, card_y + 20, btn_size, btn_size)
            btn_plus_rect = QRectF(card_x + card_w - btn_size - 3, card_y + 20, btn_size, btn_size)

            self._btn_rects[(i, "minus")] = btn_minus_rect
            self._btn_rects[(i, "plus")] = btn_plus_rect

            f_btn = QFont("Arial", 8)
            f_btn.setBold(True)

            is_minus_hov = (self.hovered_action == (i, "minus"))
            p.setBrush(QBrush(QColor("#fee2e2") if is_minus_hov else QColor("#f1f5f9")))
            p.setPen(QPen(QColor("#ef4444") if is_minus_hov else QColor("#cbd5e1"), 1))
            p.drawRoundedRect(btn_minus_rect, 3, 3)
            p.setFont(f_btn)
            p.setPen(QPen(QColor("#dc2626") if is_minus_hov else QColor("#475569"), 1))
            p.drawText(btn_minus_rect, ALIGN_CENTER, "-")

            is_plus_hov = (self.hovered_action == (i, "plus"))
            p.setBrush(QBrush(QColor("#dcfce7") if is_plus_hov else QColor("#f1f5f9")))
            p.setPen(QPen(QColor("#22c55e") if is_plus_hov else QColor("#cbd5e1"), 1))
            p.drawRoundedRect(btn_plus_rect, 3, 3)
            p.setFont(f_btn)
            p.setPen(QPen(QColor("#16a34a") if is_plus_hov else QColor("#475569"), 1))
            p.drawText(btn_plus_rect, ALIGN_CENTER, "+")

            # Ortadaki Genişlik Değeri
            f_w = QFont("Arial", 7)
            f_w.setBold(True)
            p.setFont(f_w)
            p.setPen(QPen(QColor("#0f172a"), 1))
            text_w_rect = QRectF(card_x + btn_size + 1, card_y + 19, card_w - (btn_size * 2) - 2, 16)
            p.drawText(text_w_rect, ALIGN_CENTER, f"{elem.width:.2f}m")

            # Şeride İnen Kesik Kılavuz Çizgi
            p.setPen(QPen(border_col, 1.0, PEN_STYLE_DASHLINE))
            p.drawLine(QPointF(mid_x, card_y + card_h), QPointF(mid_x, y_ground - (elem.elevation * self.ppm)))

            cur_x += ew

        p.restore()

    def _draw_bottom_dimensions(self, p, sec, x_road, y_ground):
        """Çift kademeli mimari ölçülendirme (şerit zincir ölçüsü + master kırmızı çizgi)."""
        p.save()
        cur_x = x_road
        show_subgrade = getattr(sec, "show_subgrade", True)
        theme = getattr(sec, "visual_theme", "architectural")
        is_night = (theme == "night_lighting")

        sub_bottom_y = (y_ground + 84.0) if show_subgrade else (y_ground + 14.0)
        dim_chain_y = (y_ground + 94.0) if show_subgrade else (y_ground + 28.0)
        f_dim = QFont("Arial", 7)
        f_dim.setBold(True)
        p.setFont(f_dim)

        line_col = QColor("#cbd5e1") if is_night else QColor("#334155")
        txt_col = QColor("#f8fafc") if is_night else QColor("#0f172a")
        sub_txt_col = QColor("#cbd5e1") if is_night else QColor("#64748b")

        # 1. KADEME: HER ŞERİDİN MİMARİ ZİNCİR ÖLÇÜSÜ VE ADI
        for elem in sec.elements:
            ew = elem.width * self.ppm

            # Tanıklık / Sınır Çizgileri
            p.setPen(QPen(QColor("#94a3b8"), 0.8))
            p.drawLine(QPointF(cur_x, sub_bottom_y), QPointF(cur_x, dim_chain_y + 14))

            # Ölçü çizgisi
            p.setPen(QPen(line_col, 1.0))
            p.drawLine(QPointF(cur_x, dim_chain_y), QPointF(cur_x + ew, dim_chain_y))

            # Mimari 45 derece eğik ölçü tırnakları (Slash ticks)
            p.drawLine(QPointF(cur_x - 3, dim_chain_y + 3), QPointF(cur_x + 3, dim_chain_y - 3))
            p.drawLine(QPointF(cur_x + ew - 3, dim_chain_y + 3), QPointF(cur_x + ew + 3, dim_chain_y - 3))

            # Genişlik metni (Ölçü üstü)
            p.setPen(QPen(txt_col, 1))
            p.drawText(QRectF(cur_x, dim_chain_y - 12, ew, 11), ALIGN_CENTER, f"{elem.width:.2f} m")

            # Şerit kısa işlev adı (Ölçü altı)
            f_sub = QFont("Arial", 6)
            p.setFont(f_sub)
            p.setPen(QPen(sub_txt_col, 1))
            sub_lbl = elem.label
            if len(sub_lbl) > int(ew / 5):
                sub_lbl = sub_lbl[:max(3, int(ew / 5) - 2)] + ".."
            p.drawText(QRectF(cur_x, dim_chain_y + 2, ew, 10), ALIGN_CENTER, sub_lbl)
            p.setFont(f_dim)

            cur_x += ew

        # Son eleman sağ sınır çizgisi
        p.setPen(QPen(QColor("#94a3b8"), 0.8))
        p.drawLine(QPointF(cur_x, sub_bottom_y), QPointF(cur_x, dim_chain_y + 14))

        # 2. KADEME: MASTER KIRMIZI ÇİZGİ ÖLÇÜSÜ (RIGHT-OF-WAY)
        dim_master_y = dim_chain_y + 30.0
        rx1 = x_road
        rx2 = x_road + sec.total_width * self.ppm
        rmid = (rx1 + rx2) / 2

        p.setPen(QPen(QColor("#dc2626"), 1.8))
        p.drawLine(QPointF(rx1, dim_master_y), QPointF(rx2, dim_master_y))
        p.drawLine(QPointF(rx1 - 4, dim_master_y + 4), QPointF(rx1 + 4, dim_master_y - 4))
        p.drawLine(QPointF(rx2 - 4, dim_master_y + 4), QPointF(rx2 + 4, dim_master_y - 4))

        # Tanıklık çizgileri
        p.setPen(QPen(QColor("#f87171"), 1.0, PEN_STYLE_DASHLINE))
        p.drawLine(QPointF(rx1, dim_chain_y + 14), QPointF(rx1, dim_master_y + 8))
        p.drawLine(QPointF(rx2, dim_chain_y + 14), QPointF(rx2, dim_master_y + 8))

        # Master Rozet
        box_w = 270
        p.fillRect(QRectF(rmid - box_w / 2, dim_master_y - 10, box_w, 20), QColor("#fef2f2"))
        p.setPen(QPen(QColor("#dc2626"), 1.2))
        p.drawRoundedRect(QRectF(rmid - box_w / 2, dim_master_y - 10, box_w, 20), 4, 4)

        f_master = QFont("Arial", 8)
        f_master.setBold(True)
        p.setFont(f_master)
        p.setPen(QPen(QColor("#b91c1c"), 1))
        lang = getattr(sec, "language", get_language())
        diff_txt = tr_text("canvas_balanced", lang) if abs(sec.width_difference) < 0.05 else f"{sec.total_width:.2f} m"
        p.drawText(
            QRectF(rmid - box_w / 2, dim_master_y - 10, box_w, 20),
            ALIGN_CENTER,
            tr_text("canvas_right_of_way", lang, row=sec.right_of_way, status=diff_txt),
        )

        p.restore()

    def export_to_image(self, filepath, dpi=300):
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
