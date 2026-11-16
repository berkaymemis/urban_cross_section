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
ANTIALIASING = QPainter.RenderHint.Antialiasing
SMOOTH_PIXMAP = QPainter.RenderHint.SmoothPixmapTransform

# QImage Format uyumluluğu (Qt5 vs Qt6)
FORMAT_ARGB32 = QImage.Format.Format_ARGB32

# Qt Hizalama (Alignment) uyumluluğu
ALIGN_CENTER = Qt.AlignmentFlag.AlignCenter
ALIGN_LEFT = Qt.AlignmentFlag.AlignLeft
ALIGN_RIGHT = Qt.AlignmentFlag.AlignRight
ALIGN_VCENTER = Qt.AlignmentFlag.AlignVCenter

# Qt Orientation (Splitter) uyumluluğu
ORIENTATION_HORIZONTAL = Qt.Orientation.Horizontal
ORIENTATION_VERTICAL = Qt.Orientation.Vertical

# PenStyle & BrushStyle uyumluluğu
PEN_STYLE_DASHLINE = Qt.PenStyle.DashLine
PEN_STYLE_NOPEN = Qt.PenStyle.NoPen
PEN_STYLE_SOLID = Qt.PenStyle.SolidLine
BRUSH_STYLE_NOBRUSH = Qt.BrushStyle.NoBrush

# QTableWidget SelectionBehavior uyumluluğu
SELECT_ROWS = QTableWidget.SelectionBehavior.SelectRows

# QHeaderView ResizeMode compatibility
RESIZE_STRETCH = QHeaderView.ResizeMode.Stretch

# QFrame Shape compatibility
FRAME_VLINE = QFrame.Shape.VLine
