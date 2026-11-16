# -*- coding: utf-8 -*-
"""UrbanCrossSection — Qt5 (QGIS 3) ve Qt6 (QGIS 4) Uyumluluk Katmanı (gis/compat.py)."""

from qgis.PyQt.QtCore import Qt, QSize, QPoint, QRect, QRectF, QPointF
from qgis.PyQt.QtGui import (
    QColor,
    QFont,
    QPen,
    QBrush,
    QPainter,
    QPixmap,
    QImage,
    QLinearGradient,
)
from qgis.PyQt.QtWidgets import (
    QWidget,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QTabWidget,
    QGroupBox,
    QSplitter,
    QScrollArea,
    QFileDialog,
    QMessageBox,
    QToolButton,
    QFrame,
)

# QAction: Qt5'te QtWidgets içinde, Qt6'da QtGui içindedir
try:
    from qgis.PyQt.QtGui import QAction
except ImportError:
    from qgis.PyQt.QtWidgets import QAction


# QPainter RenderHint uyumluluğu
try:
    ANTIALIASING = QPainter.RenderHint.Antialiasing
    SMOOTH_PIXMAP = QPainter.RenderHint.SmoothPixmapTransform
except AttributeError:
    ANTIALIASING = QPainter.Antialiasing
    SMOOTH_PIXMAP = QPainter.SmoothPixmapTransform

# QImage Format uyumluluğu (Qt5 vs Qt6)
try:
    FORMAT_ARGB32 = QImage.Format.Format_ARGB32
except AttributeError:
    FORMAT_ARGB32 = QImage.Format_ARGB32

# Qt Hizalama (Alignment) uyumluluğu
try:
    ALIGN_CENTER = Qt.AlignmentFlag.AlignCenter
    ALIGN_LEFT = Qt.AlignmentFlag.AlignLeft
    ALIGN_RIGHT = Qt.AlignmentFlag.AlignRight
    ALIGN_VCENTER = Qt.AlignmentFlag.AlignVCenter
except AttributeError:
    ALIGN_CENTER = Qt.AlignCenter
    ALIGN_LEFT = Qt.AlignLeft
    ALIGN_RIGHT = Qt.AlignRight
    ALIGN_VCENTER = Qt.AlignVCenter

# Qt Orientation (Splitter) uyumluluğu
try:
    ORIENTATION_HORIZONTAL = Qt.Orientation.Horizontal
    ORIENTATION_VERTICAL = Qt.Orientation.Vertical
except AttributeError:
    ORIENTATION_HORIZONTAL = Qt.Horizontal
    ORIENTATION_VERTICAL = Qt.Vertical

# PenStyle & BrushStyle uyumluluğu
try:
    PEN_STYLE_DASHLINE = Qt.PenStyle.DashLine
    PEN_STYLE_NOPEN = Qt.PenStyle.NoPen
    PEN_STYLE_SOLID = Qt.PenStyle.SolidLine
    BRUSH_STYLE_NOBRUSH = Qt.BrushStyle.NoBrush
except AttributeError:
    PEN_STYLE_DASHLINE = Qt.DashLine
    PEN_STYLE_NOPEN = Qt.NoPen
    PEN_STYLE_SOLID = Qt.SolidLine
    BRUSH_STYLE_NOBRUSH = Qt.NoBrush

# QTableWidget SelectionBehavior uyumluluğu
try:
    SELECT_ROWS = QTableWidget.SelectionBehavior.SelectRows
except AttributeError:
    SELECT_ROWS = QTableWidget.SelectRows

# QHeaderView ResizeMode compatibility
try:
    RESIZE_STRETCH = QHeaderView.ResizeMode.Stretch
except AttributeError:
    RESIZE_STRETCH = QHeaderView.Stretch

# QFrame Shape compatibility
try:
    FRAME_VLINE = QFrame.Shape.VLine
except AttributeError:
    FRAME_VLINE = QFrame.VLine
