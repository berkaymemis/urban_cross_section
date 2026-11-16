# -*- coding: utf-8 -*-
"""Generate high-res icons for UrbanCrossSection."""

import os
from qgis.PyQt.QtCore import Qt, QRectF
from qgis.PyQt.QtGui import (
    QImage,
    QPainter,
    QColor,
    QPen,
    QBrush,
    QLinearGradient,
)

icons_dir = os.path.dirname(os.path.abspath(__file__))

# Format_ARGB32 uyumluluğu (Qt5 vs Qt6)
try:
    FORMAT_ARGB32 = QImage.Format.Format_ARGB32
except AttributeError:
    FORMAT_ARGB32 = QImage.Format_ARGB32

try:
    ANTIALIASING = QPainter.RenderHint.Antialiasing
except AttributeError:
    ANTIALIASING = QPainter.Antialiasing

def create_icon(size):
    img = QImage(size, size, FORMAT_ARGB32)
    img.fill(QColor(0, 0, 0, 0))

    p = QPainter(img)
    p.setRenderHint(ANTIALIASING)

    # Arka plan yuvarlak kare (modern app icon)
    grad = QLinearGradient(0, 0, size, size)
    grad.setColorAt(0.0, QColor("#1e293b"))
    grad.setColorAt(1.0, QColor("#0f172a"))
    p.setBrush(QBrush(grad))
    p.setPen(QPen(QColor(0, 0, 0, 0)))
    radius = size * 0.22
    p.drawRoundedRect(QRectF(0, 0, size, size), radius, radius)

    # Yol kesiti çizgileri (kaldırım + yol + refüj + yol + kaldırım)
    scale = size / 100.0

    # Zemin çizgisi
    p.setPen(QPen(QColor("#64748b"), 2 * scale))
    p.drawLine(int(10 * scale), int(75 * scale), int(90 * scale), int(75 * scale))

    # Sol Kaldırım
    p.fillRect(QRectF(10 * scale, 68 * scale, 15 * scale, 7 * scale), QColor("#d1d5db"))
    # Sol Ağaç
    p.fillRect(QRectF(16 * scale, 52 * scale, 3 * scale, 16 * scale), QColor("#78350f"))
    p.setBrush(QBrush(QColor("#22c55e")))
    p.setPen(QPen(QColor(0, 0, 0, 0)))
    p.drawEllipse(QRectF(11 * scale, 38 * scale, 13 * scale, 16 * scale))

    # Bisiklet yolu (Mavi)
    p.fillRect(QRectF(25 * scale, 72 * scale, 10 * scale, 3 * scale), QColor("#0284c7"))

    # Taşıt şeritleri (Koyu gri asfalt)
    p.fillRect(QRectF(35 * scale, 72 * scale, 30 * scale, 3 * scale), QColor("#374151"))

    # Şerit ayırıcı beyaz kesik çizgi
    pen_dash = QPen(QColor("#ffffff"), 1.2 * scale)
    pen_dash.setDashPattern([3, 3])
    p.setPen(pen_dash)
    p.drawLine(int(50 * scale), int(73.5 * scale), int(50 * scale), int(73.5 * scale))

    # Araba silüeti
    p.setBrush(QBrush(QColor("#38bdf8")))
    p.setPen(QPen(QColor(0, 0, 0, 0)))
    p.drawRoundedRect(QRectF(42 * scale, 62 * scale, 16 * scale, 10 * scale), 2 * scale, 2 * scale)

    # Sağ Kaldırım
    p.fillRect(QRectF(75 * scale, 68 * scale, 15 * scale, 7 * scale), QColor("#d1d5db"))

    # Çift yönlü kesit okları (Üstte ölçülendirme oku)
    p.setPen(QPen(QColor("#ef4444"), 2 * scale))
    p.drawLine(int(10 * scale), int(25 * scale), int(90 * scale), int(25 * scale))
    # Sol ok ucu
    p.drawLine(int(10 * scale), int(25 * scale), int(16 * scale), int(21 * scale))
    p.drawLine(int(10 * scale), int(25 * scale), int(16 * scale), int(29 * scale))
    # Sağ ok ucu
    p.drawLine(int(90 * scale), int(25 * scale), int(84 * scale), int(21 * scale))
    p.drawLine(int(90 * scale), int(25 * scale), int(84 * scale), int(29 * scale))

    p.end()
    return img

if __name__ == "__main__":
    icon48 = create_icon(48)
    icon48.save(os.path.join(icons_dir, "icon.png"), "PNG")

    icon512 = create_icon(512)
    icon512.save(os.path.join(icons_dir, "icon_512.png"), "PNG")
    print("Icons generated successfully!")
