# -*- coding: utf-8 -*-
"""UrbanCrossSection — Main Dual-Mode Studio Dialog (ui/main_dialog.py).

Qt5 (QGIS 3) and Qt6 (QGIS 4) compatible.
Supports simplified Basic Mode (default) and full Advanced Mode, plus 100% English
default UI with an instant EN / TR bilingual switch.
"""

import os
from typing import Optional
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor, QFont
from qgis.PyQt.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QLineEdit,
    QGroupBox,
    QFileDialog,
    QMessageBox,
    QWidget,
    QSlider,
    QFrame,
    QTabWidget,
)
from qgis.core import (
    QgsProject,
    QgsPointXY,
    QgsRasterLayer,
    QgsVectorLayer,
    QgsWkbTypes,
)

from .canvas_widget import SectionCanvasWidget
from .profile_canvas import UrbanProfileCanvasWidget
from ..gis.compat import ORIENTATION_HORIZONTAL, ALIGN_CENTER, FRAME_VLINE
from ..core.i18n import (
    get_language,
    set_language,
    tr_text,
    retranslate_section_inplace,
    retranslate_profile_inplace,
)
from ..core.elements import ElementType, SectionElement
from ..core.presets import list_presets, get_preset_by_width, get_preset_by_id
from ..core.svg_exporter import SvgCrossSectionExporter
from ..core.profile_model import (
    UrbanProfile,
    BuildingMass,
    VegetationCluster,
    preset_profile_hillside_aa,
    preset_profile_slope_bb,
)
from ..core.profile_svg import SvgUrbanProfileExporter
from ..gis.layer_reader import get_road_line_layers, extract_selected_road_info
from ..gis.cross_line_gen import add_cross_section_to_map
from ..gis.layout_inserter import insert_section_image_to_layout
from ..gis.profile_sampler import (
    sample_profile_between_points,
    find_dem_raster_layer,
    find_slope_raster_layer,
    find_contour_vector_layer,
    find_building_polygon_layer,
    find_road_layer,
    detect_elevation_field,
    detect_building_floors_field,
)
from ..gis.map_tool_section import SectionLineMapTool


_PILL_ACTIVE = """
    QPushButton {
        font-weight: bold;
        font-size: 11px;
        padding: 4px 12px;
        background-color: #2563eb;
        color: #ffffff;
        border: 1px solid #1d4ed8;
        border-radius: 5px;
    }
"""
_PILL_IDLE = """
    QPushButton {
        font-weight: bold;
        font-size: 11px;
        padding: 4px 12px;
        background-color: #f1f5f9;
        color: #334155;
        border: 1px solid #cbd5e1;
        border-radius: 5px;
    }
    QPushButton:hover {
        background-color: #e2e8f0;
    }
"""


class UrbanCrossSectionDialog(QDialog):
    """Unified Street Cross-Section & 1:1000 Urban Terrain Profile Studio Dialog."""

    def __init__(self, iface=None, parent=None, language: str = "en"):
        super().__init__(parent)
        set_language(language)
        self.iface = iface
        self.resize(1240, 800)
        self.setMinimumSize(960, 680)

        # Mode & Language state (Basic + English by default)
        self.is_advanced_mode = False
        self.is_collapsed = False
        self._updating_ui = False

        # Mode 1 State: Street Cross-Section
        self.current_section = get_preset_by_id("15m", lang=get_language())
        self.selected_road_geom = None
        self.selected_road_name = "Street"

        # Mode 2 State: 1:1000 Urban Profile & Terrain A-B Section
        self.current_profile = preset_profile_hillside_aa(lang=get_language())
        self.master_profile = self.current_profile
        self.profile_segments = []
        self.map_tool_section = None
        self.last_pt_a = None
        self.last_pt_b = None

        self._init_ui()
        self._populate_presets()
        self._sync_ui_from_section()
        self._refresh_topography_layers()
        self._sync_ui_from_profile()
        self._apply_ui_mode()
        self._retranslate_ui()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 8, 12, 10)
        root_layout.setSpacing(6)

        # ---------------------------------------------------------------------
        # HEADER BAR (Brand + Basic/Advanced Switch + EN/TR Switch + Collapse)
        # ---------------------------------------------------------------------
        top_ctrl_bar = QHBoxLayout()
        top_ctrl_bar.setContentsMargins(2, 0, 2, 0)
        top_ctrl_bar.setSpacing(8)

        self.lbl_brand = QLabel()
        top_ctrl_bar.addWidget(self.lbl_brand)
        top_ctrl_bar.addStretch()

        # Basic / Advanced segmented switch
        self.lbl_mode = QLabel()
        self.lbl_mode.setStyleSheet("font-weight: bold; font-size: 11px; color: #334155;")
        top_ctrl_bar.addWidget(self.lbl_mode)

        self.btn_mode_basic = QPushButton()
        self.btn_mode_basic.setCheckable(True)
        self.btn_mode_basic.setChecked(True)
        self.btn_mode_basic.clicked.connect(lambda: self.set_advanced_mode(False))
        top_ctrl_bar.addWidget(self.btn_mode_basic)

        self.btn_mode_advanced = QPushButton()
        self.btn_mode_advanced.setCheckable(True)
        self.btn_mode_advanced.setChecked(False)
        self.btn_mode_advanced.clicked.connect(lambda: self.set_advanced_mode(True))
        top_ctrl_bar.addWidget(self.btn_mode_advanced)

        sep1 = QFrame()
        sep1.setFrameShape(FRAME_VLINE)
        sep1.setStyleSheet("color: #cbd5e1;")
        top_ctrl_bar.addWidget(sep1)

        # EN / TR Language segmented switch
        self.lbl_lang = QLabel()
        self.lbl_lang.setStyleSheet("font-weight: bold; font-size: 11px; color: #334155;")
        top_ctrl_bar.addWidget(self.lbl_lang)

        self.btn_lang_en = QPushButton("EN")
        self.btn_lang_en.setCheckable(True)
        self.btn_lang_en.setChecked(get_language() == "en")
        self.btn_lang_en.clicked.connect(lambda: self.set_ui_language("en"))
        top_ctrl_bar.addWidget(self.btn_lang_en)

        self.btn_lang_tr = QPushButton("TR")
        self.btn_lang_tr.setCheckable(True)
        self.btn_lang_tr.setChecked(get_language() == "tr")
        self.btn_lang_tr.clicked.connect(lambda: self.set_ui_language("tr"))
        top_ctrl_bar.addWidget(self.btn_lang_tr)

        sep2 = QFrame()
        sep2.setFrameShape(FRAME_VLINE)
        sep2.setStyleSheet("color: #cbd5e1;")
        top_ctrl_bar.addWidget(sep2)

        self.btn_minimize_drawer = QPushButton()
        self.btn_minimize_drawer.clicked.connect(self._on_toggle_drawer_clicked)
        top_ctrl_bar.addWidget(self.btn_minimize_drawer)

        root_layout.addLayout(top_ctrl_bar)

        # ---------------------------------------------------------------------
        # COMPACT MAP-PICKING MINI BAR
        # ---------------------------------------------------------------------
        self.mini_bar_widget = QFrame()
        self.mini_bar_widget.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1e293b, stop:1 #0f172a);
                border: 2px solid #38bdf8;
                border-radius: 8px;
                padding: 6px 14px;
            }
        """)
        mb_layout = QHBoxLayout(self.mini_bar_widget)
        mb_layout.setContentsMargins(8, 4, 8, 4)
        mb_layout.setSpacing(10)

        self.lbl_mini_status = QLabel()
        self.lbl_mini_status.setStyleSheet("color: #f8fafc; font-weight: bold; font-size: 12px;")
        mb_layout.addWidget(self.lbl_mini_status, 1)

        self.lbl_mini_look = QLabel()
        self.lbl_mini_look.setStyleSheet("color: #cbd5e1; font-weight: bold; font-size: 11px;")
        mb_layout.addWidget(self.lbl_mini_look)

        self.combo_mini_look = QComboBox()
        self.combo_mini_look.setStyleSheet("""
            QComboBox {
                font-weight: bold;
                font-size: 11px;
                padding: 4px 8px;
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #475569;
                border-radius: 5px;
            }
            QComboBox QAbstractItemView {
                background-color: #1e293b;
                color: #f8fafc;
                selection-background-color: #38bdf8;
                selection-color: #0f172a;
            }
        """)
        self.combo_mini_look.currentIndexChanged.connect(self._on_mini_look_changed)
        mb_layout.addWidget(self.combo_mini_look)

        self.btn_mini_expand = QPushButton()
        self.btn_mini_expand.setStyleSheet("""
            QPushButton {
                font-weight: bold;
                font-size: 11px;
                padding: 5px 14px;
                background-color: #38bdf8;
                color: #0f172a;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #7dd3fc;
            }
        """)
        self.btn_mini_expand.clicked.connect(lambda: self.toggle_collapse(False))
        mb_layout.addWidget(self.btn_mini_expand)

        self.btn_mini_cancel = QPushButton()
        self.btn_mini_cancel.setStyleSheet("""
            QPushButton {
                font-weight: bold;
                font-size: 11px;
                padding: 5px 10px;
                background-color: #ef4444;
                color: #ffffff;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #dc2626;
            }
        """)
        self.btn_mini_cancel.clicked.connect(self._on_mini_bar_cancel)
        mb_layout.addWidget(self.btn_mini_cancel)

        self.mini_bar_widget.setVisible(False)
        root_layout.addWidget(self.mini_bar_widget)

        # ---------------------------------------------------------------------
        # MAIN TABS
        # ---------------------------------------------------------------------
        self.main_tabs = QTabWidget()
        self.main_tabs.setStyleSheet("""
            QTabBar::tab {
                font-size: 12px;
                font-weight: bold;
                padding: 8px 20px;
                border: 1px solid #cbd5e1;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                background-color: #f1f5f9;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background-color: #ffffff;
                color: #2563eb;
                border-top: 3px solid #2563eb;
            }
        """)

        tab_streetmix = QWidget()
        self._build_streetmix_tab(tab_streetmix)
        self.main_tabs.addTab(tab_streetmix, "")

        tab_profile = QWidget()
        self._build_profile_tab(tab_profile)
        self.main_tabs.addTab(tab_profile, "")

        root_layout.addWidget(self.main_tabs)

    # =========================================================================
    # TAB 1: STREET CROSS-SECTION UI
    # =========================================================================

    def _build_streetmix_tab(self, parent_widget):
        layout = QVBoxLayout(parent_widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # 1. Clean Top Bar (Basic: Template, Width, Style, Read Map Road | Advanced: + Street Name)
        top_frame = QFrame()
        top_frame.setStyleSheet("background-color: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 4px;")
        top_layout = QHBoxLayout(top_frame)
        top_layout.setContentsMargins(10, 4, 10, 4)
        top_layout.setSpacing(8)

        self.lbl_template = QLabel()
        self.lbl_template.setStyleSheet("font-weight: bold;")
        top_layout.addWidget(self.lbl_template)
        self.combo_presets = QComboBox()
        self.combo_presets.setStyleSheet("padding: 4px 8px; font-weight: bold;")
        self.combo_presets.currentIndexChanged.connect(self._on_preset_changed)
        top_layout.addWidget(self.combo_presets, 3)

        self.lbl_road_name = QLabel()
        self.lbl_road_name.setStyleSheet("font-weight: bold;")
        top_layout.addWidget(self.lbl_road_name)
        self.txt_road_name = QLineEdit(self.current_section.name)
        self.txt_road_name.setStyleSheet("padding: 4px 6px;")
        self.txt_road_name.textChanged.connect(self._on_road_name_changed)
        top_layout.addWidget(self.txt_road_name, 2)

        self.lbl_corridor_width = QLabel()
        self.lbl_corridor_width.setStyleSheet("font-weight: bold;")
        top_layout.addWidget(self.lbl_corridor_width)
        self.spin_row = QDoubleSpinBox()
        self.spin_row.setRange(2.0, 120.0)
        self.spin_row.setSingleStep(0.5)
        self.spin_row.setDecimals(2)
        self.spin_row.setValue(15.0)
        self.spin_row.setStyleSheet("padding: 4px; font-weight: bold;")
        self.spin_row.valueChanged.connect(self._on_row_width_changed)
        top_layout.addWidget(self.spin_row, 1)

        self.lbl_theme = QLabel()
        self.lbl_theme.setStyleSheet("font-weight: bold;")
        top_layout.addWidget(self.lbl_theme)
        self.combo_visual_theme = QComboBox()
        self.combo_visual_theme.setStyleSheet("padding: 4px 6px; font-weight: bold;")
        self.combo_visual_theme.currentIndexChanged.connect(self._on_visual_theme_changed)
        top_layout.addWidget(self.combo_visual_theme, 2)

        self.btn_select_map = QPushButton()
        self.btn_select_map.setStyleSheet("font-weight: bold; padding: 5px 12px; background-color: #e0f2fe; color: #0369a1; border: 1px solid #38bdf8; border-radius: 6px;")
        self.btn_select_map.clicked.connect(self._on_read_selected_road)
        top_layout.addWidget(self.btn_select_map, 2)

        layout.addWidget(top_frame)

        # 2. Balance Badge
        self.lbl_status = QLabel()
        self.lbl_status.setAlignment(ALIGN_CENTER)
        self.lbl_status.setFixedHeight(30)
        self.lbl_status.setStyleSheet("font-size: 11px; font-weight: bold; border-radius: 6px; padding: 2px 10px;")
        layout.addWidget(self.lbl_status)

        # 3. Live Street Canvas
        self.canvas = SectionCanvasWidget(section=self.current_section)
        self.canvas.elementClicked.connect(self._on_canvas_element_clicked)
        self.canvas.elementWidthAdjusted.connect(self._on_canvas_width_adjusted)
        self.canvas.elementDeleteRequested.connect(self._on_canvas_delete_requested)
        self.canvas.utilityToggled.connect(self._on_canvas_utility_toggled)
        layout.addWidget(self.canvas, 1)

        # 4. Selected Strip Bar (Basic: Width + Move + Delete | Advanced: + Slider & Furniture)
        inspector_frame = QFrame()
        inspector_frame.setStyleSheet("background-color: #ffffff; border: 1.5px solid #cbd5e1; border-radius: 8px; padding: 4px;")
        insp_layout = QVBoxLayout(inspector_frame)
        insp_layout.setContentsMargins(8, 5, 8, 5)
        insp_layout.setSpacing(5)

        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(8)

        self.lbl_selected_title = QLabel()
        row1_layout.addWidget(self.lbl_selected_title, 2)

        self.btn_minus_025 = QPushButton("- 0.25m")
        self.btn_minus_025.setStyleSheet("font-weight: bold; padding: 4px 8px; background-color: #fee2e2; color: #991b1b; border: 1px solid #f87171; border-radius: 4px;")
        self.btn_minus_025.clicked.connect(lambda: self._adjust_selected_width(-0.25))
        row1_layout.addWidget(self.btn_minus_025)

        self.spin_elem_width = QDoubleSpinBox()
        self.spin_elem_width.setRange(0.2, 30.0)
        self.spin_elem_width.setSingleStep(0.25)
        self.spin_elem_width.setDecimals(2)
        self.spin_elem_width.setStyleSheet("font-weight: bold; padding: 3px;")
        self.spin_elem_width.valueChanged.connect(self._on_elem_width_spin_changed)
        row1_layout.addWidget(self.spin_elem_width)

        self.btn_plus_025 = QPushButton("+ 0.25m")
        self.btn_plus_025.setStyleSheet("font-weight: bold; padding: 4px 8px; background-color: #dcfce7; color: #166534; border: 1px solid #86efac; border-radius: 4px;")
        self.btn_plus_025.clicked.connect(lambda: self._adjust_selected_width(0.25))
        row1_layout.addWidget(self.btn_plus_025)

        self.slider_elem_width = QSlider(ORIENTATION_HORIZONTAL)
        self.slider_elem_width.setRange(20, 1500)
        self.slider_elem_width.valueChanged.connect(self._on_slider_width_changed)
        row1_layout.addWidget(self.slider_elem_width, 2)

        self.btn_move_left = QPushButton()
        self.btn_move_left.clicked.connect(self._on_move_element_left)
        row1_layout.addWidget(self.btn_move_left)

        self.btn_move_right = QPushButton()
        self.btn_move_right.clicked.connect(self._on_move_element_right)
        row1_layout.addWidget(self.btn_move_right)

        self.btn_del_elem = QPushButton()
        self.btn_del_elem.setStyleSheet("font-weight: bold; padding: 4px 10px; background-color: #fee2e2; color: #b91c1c; border: 1px solid #fca5a5; border-radius: 4px;")
        self.btn_del_elem.clicked.connect(self._on_delete_element)
        row1_layout.addWidget(self.btn_del_elem)

        insp_layout.addLayout(row1_layout)

        # Row 2 (Advanced only): Furniture, Vehicles, Pedestrians
        self.insp_adv_widget = QWidget()
        row2_layout = QHBoxLayout(self.insp_adv_widget)
        row2_layout.setContentsMargins(0, 2, 0, 0)
        row2_layout.setSpacing(10)

        self.chk_trees = QCheckBox()
        self.chk_trees.toggled.connect(self._on_tree_toggled)
        row2_layout.addWidget(self.chk_trees)

        self.chk_lighting = QCheckBox()
        self.chk_lighting.toggled.connect(self._on_lighting_toggled)
        row2_layout.addWidget(self.chk_lighting)

        self.chk_bench = QCheckBox()
        self.chk_bench.toggled.connect(self._on_bench_toggled)
        row2_layout.addWidget(self.chk_bench)

        self.chk_bus_shelter = QCheckBox()
        self.chk_bus_shelter.toggled.connect(self._on_bus_shelter_toggled)
        row2_layout.addWidget(self.chk_bus_shelter)

        self.chk_tactile = QCheckBox()
        self.chk_tactile.toggled.connect(self._on_tactile_toggled)
        row2_layout.addWidget(self.chk_tactile)

        self.chk_bike_rack = QCheckBox()
        self.chk_bike_rack.toggled.connect(self._on_bike_rack_toggled)
        row2_layout.addWidget(self.chk_bike_rack)

        row2_layout.addSpacing(8)
        self.lbl_vehicle = QLabel()
        self.lbl_vehicle.setStyleSheet("font-weight: bold;")
        row2_layout.addWidget(self.lbl_vehicle)
        self.combo_vehicle = QComboBox()
        self.combo_vehicle.currentIndexChanged.connect(self._on_vehicle_combo_changed)
        row2_layout.addWidget(self.combo_vehicle)

        self.lbl_people = QLabel()
        self.lbl_people.setStyleSheet("font-weight: bold;")
        row2_layout.addWidget(self.lbl_people)
        self.spin_pedestrians = QSpinBox()
        self.spin_pedestrians.setRange(0, 4)
        self.spin_pedestrians.valueChanged.connect(self._on_pedestrians_spin_changed)
        row2_layout.addWidget(self.spin_pedestrians)

        row2_layout.addStretch()
        insp_layout.addWidget(self.insp_adv_widget)
        layout.addWidget(inspector_frame)

        # 5. Strip Quick-Add Shelf + Advanced Drawers
        palette_frame = QFrame()
        palette_frame.setStyleSheet("background-color: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 8px; padding: 4px;")
        pal_outer = QVBoxLayout(palette_frame)
        pal_outer.setContentsMargins(8, 4, 8, 4)
        pal_outer.setSpacing(4)

        pal_title_layout = QHBoxLayout()
        self.lbl_add_strip = QLabel()
        self.lbl_add_strip.setStyleSheet("font-weight: bold; font-size: 11px;")
        pal_title_layout.addWidget(self.lbl_add_strip)
        pal_title_layout.addStretch()

        self.btn_toggle_utilities = QPushButton()
        self.btn_toggle_utilities.setStyleSheet("font-size: 11px; font-weight: bold; padding: 2px 10px; background-color: #e0f2fe; color: #0369a1; border: 1px solid #38bdf8; border-radius: 4px;")
        self.btn_toggle_utilities.clicked.connect(self._toggle_utilities_drawer)
        pal_title_layout.addWidget(self.btn_toggle_utilities)

        self.btn_toggle_buildings = QPushButton()
        self.btn_toggle_buildings.setStyleSheet("font-size: 11px; padding: 2px 8px; background-color: #ffffff; border: 1px solid #94a3b8; border-radius: 4px;")
        self.btn_toggle_buildings.clicked.connect(self._toggle_buildings_drawer)
        pal_title_layout.addWidget(self.btn_toggle_buildings)
        pal_outer.addLayout(pal_title_layout)

        shelf_layout = QHBoxLayout()
        shelf_layout.setSpacing(5)

        palette_specs = [
            ("pal_sidewalk", ElementType.SIDEWALK, 2.0, {"elevation": 0.15, "surface_color": "#e2e8f0", "has_curb": True, "has_tactile": True, "pedestrian_count": 1}, "#f8fafc", "#0284c7", False),
            ("pal_landscape", ElementType.LANDSCAPE, 1.5, {"elevation": 0.15, "surface_color": "#86efac", "has_trees": True}, "#f0fdf4", "#16a34a", False),
            ("pal_bike", ElementType.BIKE_LANE, 1.5, {"elevation": 0.05, "surface_color": "#0284c7", "marking": "bike_stencil", "cyclist_count": 1}, "#f0fdfa", "#0d9488", False),
            ("pal_vehicle", ElementType.VEHICLE_LANE, 3.25, {"elevation": 0.0, "surface_color": "#334155", "vehicle_type": "car", "marking": "dashed_white"}, "#f8fafc", "#475569", False),
            ("pal_bus", ElementType.BUS_LANE, 3.5, {"elevation": 0.0, "surface_color": "#334155", "vehicle_type": "bus", "marking": "solid_white"}, "#fefce8", "#ca8a04", False),
            ("pal_parking", ElementType.PARKING, 2.0, {"elevation": 0.0, "surface_color": "#475569", "vehicle_type": "car"}, "#f1f5f9", "#64748b", False),
            ("pal_median", ElementType.MEDIAN, 2.0, {"elevation": 0.20, "surface_color": "#22c55e", "has_trees": True, "has_lighting": True}, "#ecfdf5", "#059669", False),
            ("pal_tram", ElementType.TRAM_LANE, 6.0, {"elevation": 0.05, "surface_color": "#10b981"}, "#faf5ff", "#9333ea", True),
            ("pal_parklet", ElementType.PARKLET, 3.0, {"elevation": 0.15, "surface_color": "#fed7aa", "has_bench": True}, "#fff7ed", "#ea580c", True),
            ("pal_buffer", ElementType.BUFFER, 0.5, {"elevation": 0.15, "surface_color": "#94a3b8", "has_curb": True}, "#f3f4f6", "#4b5563", True),
        ]

        self._palette_buttons = []
        self._palette_adv_buttons = []
        for key, etype, w, kw, bg, fg, adv_only in palette_specs:
            btn = QPushButton()
            btn.setStyleSheet(f"font-weight: bold; font-size: 11px; padding: 5px 8px; background-color: {bg}; color: {fg}; border: 1px solid #cbd5e1; border-radius: 5px;")
            btn.clicked.connect(lambda checked=False, t=etype, width=w, extra=kw: self._quick_add_element(t, width, **extra))
            shelf_layout.addWidget(btn)
            self._palette_buttons.append((btn, key))
            if adv_only:
                self._palette_adv_buttons.append(btn)

        pal_outer.addLayout(shelf_layout)

        # Advanced Drawer 1: Utilities & Visual Layers
        self.utility_drawer = QFrame()
        self.utility_drawer.setVisible(False)
        self.utility_drawer.setStyleSheet("background-color: #ffffff; border: 1px solid #93c5fd; border-radius: 6px; padding: 4px;")
        util_vbox = QVBoxLayout(self.utility_drawer)
        util_vbox.setContentsMargins(6, 3, 6, 3)
        util_vbox.setSpacing(4)

        util_row1 = QHBoxLayout()
        util_row1.setSpacing(8)
        self.lbl_utilities = QLabel()
        self.lbl_utilities.setStyleSheet("font-weight: bold;")
        util_row1.addWidget(self.lbl_utilities)

        self.chk_util_water = QCheckBox()
        self.chk_util_water.setChecked(True)
        self.chk_util_water.toggled.connect(self._on_utilities_changed)
        util_row1.addWidget(self.chk_util_water)

        self.chk_util_telecom = QCheckBox()
        self.chk_util_telecom.setChecked(True)
        self.chk_util_telecom.toggled.connect(self._on_utilities_changed)
        util_row1.addWidget(self.chk_util_telecom)

        self.chk_util_power = QCheckBox()
        self.chk_util_power.setChecked(True)
        self.chk_util_power.toggled.connect(self._on_utilities_changed)
        util_row1.addWidget(self.chk_util_power)

        self.chk_util_gas = QCheckBox()
        self.chk_util_gas.setChecked(True)
        self.chk_util_gas.toggled.connect(self._on_utilities_changed)
        util_row1.addWidget(self.chk_util_gas)

        self.chk_util_drainage = QCheckBox()
        self.chk_util_drainage.setChecked(True)
        self.chk_util_drainage.toggled.connect(self._on_utilities_changed)
        util_row1.addWidget(self.chk_util_drainage)

        self.chk_util_sewer = QCheckBox()
        self.chk_util_sewer.setChecked(False)
        self.chk_util_sewer.toggled.connect(self._on_utilities_changed)
        util_row1.addWidget(self.chk_util_sewer)

        self.chk_util_gallery = QCheckBox()
        self.chk_util_gallery.setChecked(False)
        self.chk_util_gallery.toggled.connect(self._on_utilities_changed)
        util_row1.addWidget(self.chk_util_gallery)

        self.btn_util_all = QPushButton()
        self.btn_util_all.setStyleSheet("font-size: 10px; font-weight: bold; padding: 2px 6px; background-color: #dcfce7; color: #166534; border: 1px solid #86efac; border-radius: 4px;")
        self.btn_util_all.clicked.connect(lambda: self._set_all_utilities(True))
        util_row1.addWidget(self.btn_util_all)

        self.btn_util_none = QPushButton()
        self.btn_util_none.setStyleSheet("font-size: 10px; font-weight: bold; padding: 2px 6px; background-color: #fee2e2; color: #991b1b; border: 1px solid #fca5a5; border-radius: 4px;")
        self.btn_util_none.clicked.connect(lambda: self._set_all_utilities(False))
        util_row1.addWidget(self.btn_util_none)

        util_row1.addStretch()
        util_vbox.addLayout(util_row1)

        util_row2 = QHBoxLayout()
        util_row2.setSpacing(10)
        self.lbl_visual_layers = QLabel()
        self.lbl_visual_layers.setStyleSheet("font-weight: bold;")
        util_row2.addWidget(self.lbl_visual_layers)

        self.chk_show_subgrade = QCheckBox()
        self.chk_show_subgrade.setChecked(True)
        self.chk_show_subgrade.toggled.connect(self._on_visual_options_changed)
        util_row2.addWidget(self.chk_show_subgrade)

        self.chk_show_buildings = QCheckBox()
        self.chk_show_buildings.setChecked(True)
        self.chk_show_buildings.toggled.connect(self._on_visual_options_changed)
        util_row2.addWidget(self.chk_show_buildings)

        self.chk_show_slopes = QCheckBox()
        self.chk_show_slopes.setChecked(True)
        self.chk_show_slopes.toggled.connect(self._on_visual_options_changed)
        util_row2.addWidget(self.chk_show_slopes)

        self.chk_show_cards = QCheckBox()
        self.chk_show_cards.setChecked(True)
        self.chk_show_cards.toggled.connect(self._on_visual_options_changed)
        util_row2.addWidget(self.chk_show_cards)

        self.chk_show_dimensions = QCheckBox()
        self.chk_show_dimensions.setChecked(True)
        self.chk_show_dimensions.toggled.connect(self._on_visual_options_changed)
        util_row2.addWidget(self.chk_show_dimensions)

        util_row2.addStretch()
        util_vbox.addLayout(util_row2)

        pal_outer.addWidget(self.utility_drawer)

        # Advanced Drawer 2: Side Buildings
        self.bldg_drawer = QFrame()
        self.bldg_drawer.setVisible(False)
        self.bldg_drawer.setStyleSheet("background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px; padding: 4px;")
        bldg_layout = QHBoxLayout(self.bldg_drawer)
        bldg_layout.setContentsMargins(6, 2, 6, 2)

        self.lbl_left_floors = QLabel()
        self.lbl_left_floors.setStyleSheet("font-weight: bold;")
        bldg_layout.addWidget(self.lbl_left_floors)
        self.spin_left_floors = QSpinBox()
        self.spin_left_floors.setRange(1, 20)
        self.spin_left_floors.setValue(5)
        self.spin_left_floors.valueChanged.connect(self._on_building_changed)
        bldg_layout.addWidget(self.spin_left_floors)

        self.lbl_left_setback = QLabel()
        bldg_layout.addWidget(self.lbl_left_setback)
        self.spin_left_setback = QDoubleSpinBox()
        self.spin_left_setback.setRange(0.0, 20.0)
        self.spin_left_setback.setValue(3.5)
        self.spin_left_setback.valueChanged.connect(self._on_building_changed)
        bldg_layout.addWidget(self.spin_left_setback)

        self.lbl_left_sign = QLabel()
        bldg_layout.addWidget(self.lbl_left_sign)
        self.txt_left_shop = QLineEdit(self.current_section.left_building.shop_name)
        self.txt_left_shop.textChanged.connect(self._on_building_changed)
        bldg_layout.addWidget(self.txt_left_shop)

        bldg_layout.addSpacing(14)
        self.lbl_right_floors = QLabel()
        self.lbl_right_floors.setStyleSheet("font-weight: bold;")
        bldg_layout.addWidget(self.lbl_right_floors)
        self.spin_right_floors = QSpinBox()
        self.spin_right_floors.setRange(1, 20)
        self.spin_right_floors.setValue(5)
        self.spin_right_floors.valueChanged.connect(self._on_building_changed)
        bldg_layout.addWidget(self.spin_right_floors)

        self.lbl_right_setback = QLabel()
        bldg_layout.addWidget(self.lbl_right_setback)
        self.spin_right_setback = QDoubleSpinBox()
        self.spin_right_setback.setRange(0.0, 20.0)
        self.spin_right_setback.setValue(3.5)
        self.spin_right_setback.valueChanged.connect(self._on_building_changed)
        bldg_layout.addWidget(self.spin_right_setback)

        self.lbl_right_sign = QLabel()
        bldg_layout.addWidget(self.lbl_right_sign)
        self.txt_right_shop = QLineEdit(self.current_section.right_building.shop_name)
        self.txt_right_shop.textChanged.connect(self._on_building_changed)
        bldg_layout.addWidget(self.txt_right_shop)

        pal_outer.addWidget(self.bldg_drawer)
        layout.addWidget(palette_frame)

        # 6. Bottom Action Row
        action_layout = QHBoxLayout()
        action_layout.setSpacing(8)

        self.btn_map_line = QPushButton()
        self.btn_map_line.setStyleSheet("font-weight: bold; padding: 6px 14px; background-color: #fee2e2; color: #991b1b; border: 1px solid #f87171; border-radius: 6px;")
        self.btn_map_line.clicked.connect(self._on_add_map_line)
        action_layout.addWidget(self.btn_map_line)

        self.btn_print_layout = QPushButton()
        self.btn_print_layout.setStyleSheet("font-weight: bold; padding: 6px 14px; background-color: #fef08a; color: #854d0e; border: 1px solid #eab308; border-radius: 6px;")
        self.btn_print_layout.clicked.connect(self._on_add_to_print_layout)
        action_layout.addWidget(self.btn_print_layout)

        self.btn_export_svg = QPushButton()
        self.btn_export_svg.setStyleSheet("font-weight: bold; padding: 6px 14px; background-color: #ecfdf5; color: #065f46; border: 1px solid #34d399; border-radius: 6px;")
        self.btn_export_svg.clicked.connect(self._on_export_svg)
        action_layout.addWidget(self.btn_export_svg)

        self.btn_export_png = QPushButton()
        self.btn_export_png.setStyleSheet("font-weight: bold; padding: 6px 14px; background-color: #e0e7ff; color: #3730a3; border: 1px solid #818cf8; border-radius: 6px;")
        self.btn_export_png.clicked.connect(self._on_export_png)
        action_layout.addWidget(self.btn_export_png)

        action_layout.addStretch()

        self.btn_close = QPushButton()
        self.btn_close.setStyleSheet("padding: 6px 18px; font-weight: bold; border-radius: 6px;")
        self.btn_close.clicked.connect(self.accept)
        action_layout.addWidget(self.btn_close)

        layout.addLayout(action_layout)

    # =========================================================================
    # TAB 2: 1:1000 URBAN PROFILE & TOPOGRAPHY UI
    # =========================================================================

    def _build_profile_tab(self, parent_widget):
        layout = QVBoxLayout(parent_widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # 1. Profile Style Bar (Advanced Mode)
        self.prof_top_frame = QFrame()
        self.prof_top_frame.setStyleSheet("background-color: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 4px;")
        pt_layout = QHBoxLayout(self.prof_top_frame)
        pt_layout.setContentsMargins(10, 4, 10, 4)
        pt_layout.setSpacing(8)

        self.lbl_profile_preset = QLabel()
        self.lbl_profile_preset.setStyleSheet("font-weight: bold;")
        pt_layout.addWidget(self.lbl_profile_preset)
        self.combo_profile_presets = QComboBox()
        self.combo_profile_presets.currentIndexChanged.connect(self._on_profile_preset_changed)
        pt_layout.addWidget(self.combo_profile_presets, 2)

        self.lbl_profile_title = QLabel()
        self.lbl_profile_title.setStyleSheet("font-weight: bold;")
        pt_layout.addWidget(self.lbl_profile_title)
        self.txt_profile_title = QLineEdit(self.current_profile.title)
        self.txt_profile_title.setStyleSheet("font-weight: bold; padding: 3px 6px;")
        self.txt_profile_title.textChanged.connect(self._on_profile_title_changed)
        pt_layout.addWidget(self.txt_profile_title, 2)

        self.lbl_sky = QLabel()
        self.lbl_sky.setStyleSheet("font-weight: bold;")
        pt_layout.addWidget(self.lbl_sky)
        self.combo_sky = QComboBox()
        self.combo_sky.currentIndexChanged.connect(self._on_sky_theme_changed)
        pt_layout.addWidget(self.combo_sky, 1)

        self.lbl_exag = QLabel()
        self.lbl_exag.setStyleSheet("font-weight: bold;")
        pt_layout.addWidget(self.lbl_exag)
        self.combo_exag = QComboBox()
        self.combo_exag.currentIndexChanged.connect(self._on_vertical_exaggeration_changed)
        pt_layout.addWidget(self.combo_exag, 1)

        layout.addWidget(self.prof_top_frame)

        # 1.5. Multi-Sheet Segment Bar (Shown automatically when total_length > 700m or in Advanced Mode)
        self.segment_box = QFrame()
        self.segment_box.setStyleSheet("QFrame { background-color: #f8fafc; border: 1.5px solid #cbd5e1; border-radius: 8px; padding: 4px; }")
        sb_layout = QHBoxLayout(self.segment_box)
        sb_layout.setContentsMargins(8, 4, 8, 4)
        sb_layout.setSpacing(8)

        self.lbl_segment = QLabel()
        self.lbl_segment.setStyleSheet("font-weight: bold;")
        sb_layout.addWidget(self.lbl_segment)

        self.combo_segment = QComboBox()
        self.combo_segment.setStyleSheet("font-weight: bold; padding: 4px 8px; background-color: #ffffff; border: 1px solid #94a3b8; border-radius: 4px;")
        self.combo_segment.currentIndexChanged.connect(self._on_segment_changed)
        sb_layout.addWidget(self.combo_segment, 3)

        self.btn_prev_segment = QPushButton()
        self.btn_prev_segment.setStyleSheet("font-weight: bold; padding: 4px 10px; background-color: #e2e8f0; border-radius: 4px;")
        self.btn_prev_segment.clicked.connect(self._on_prev_segment_clicked)
        sb_layout.addWidget(self.btn_prev_segment)

        self.btn_next_segment = QPushButton()
        self.btn_next_segment.setStyleSheet("font-weight: bold; padding: 4px 10px; background-color: #e2e8f0; border-radius: 4px;")
        self.btn_next_segment.clicked.connect(self._on_next_segment_clicked)
        sb_layout.addWidget(self.btn_next_segment)

        self.btn_export_all_segments = QPushButton()
        self.btn_export_all_segments.setStyleSheet("font-weight: bold; padding: 4px 12px; background-color: #dcfce7; color: #166534; border: 1px solid #86efac; border-radius: 4px;")
        self.btn_export_all_segments.clicked.connect(self._on_export_all_segments)
        sb_layout.addWidget(self.btn_export_all_segments)

        layout.addWidget(self.segment_box)

        # 2. Elevation & Building Extraction Box (Basic: 1 clean row | Advanced: full GIS field controls)
        self.topo_box = QGroupBox()
        self.topo_box.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1.5px solid #94a3b8;
                border-radius: 8px;
                margin-top: 6px;
                padding-top: 10px;
                background-color: #f8fafc;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 14px;
                padding: 0 5px;
                color: #0f172a;
            }
        """)
        topo_layout = QVBoxLayout(self.topo_box)
        topo_layout.setContentsMargins(10, 6, 10, 8)
        topo_layout.setSpacing(6)

        # Row 1 (Basic + Advanced primary inputs)
        t_row1 = QHBoxLayout()
        t_row1.setSpacing(8)

        self.lbl_source_mode = QLabel()
        self.lbl_source_mode.setStyleSheet("font-weight: bold;")
        t_row1.addWidget(self.lbl_source_mode)
        self.combo_topo_mode = QComboBox()
        self.combo_topo_mode.currentIndexChanged.connect(self._on_topography_mode_changed)
        t_row1.addWidget(self.combo_topo_mode, 2)

        self.lbl_dem = QLabel()
        t_row1.addWidget(self.lbl_dem)
        self.combo_dem_layer = QComboBox()
        t_row1.addWidget(self.combo_dem_layer, 2)

        self.btn_load_dem = QPushButton()
        self.btn_load_dem.setStyleSheet("font-weight: bold; padding: 4px 8px; background-color: #e0f2fe; color: #0369a1; border: 1px solid #7dd3fc; border-radius: 4px;")
        self.btn_load_dem.clicked.connect(self._on_load_dem_file)
        t_row1.addWidget(self.btn_load_dem)

        self.lbl_contour = QLabel()
        t_row1.addWidget(self.lbl_contour)
        self.combo_contour_layer = QComboBox()
        self.combo_contour_layer.currentIndexChanged.connect(self._update_contour_fields)
        t_row1.addWidget(self.combo_contour_layer, 2)

        self.btn_load_contour = QPushButton()
        self.btn_load_contour.setStyleSheet("font-weight: bold; padding: 4px 8px; background-color: #ecfdf5; color: #065f46; border: 1px solid #a7f3d0; border-radius: 4px;")
        self.btn_load_contour.clicked.connect(self._on_load_contour_file)
        t_row1.addWidget(self.btn_load_contour)

        self.lbl_bldg_layer = QLabel()
        t_row1.addWidget(self.lbl_bldg_layer)
        self.combo_bldg_layer = QComboBox()
        self.combo_bldg_layer.currentIndexChanged.connect(self._update_bldg_fields)
        t_row1.addWidget(self.combo_bldg_layer, 2)

        self.lbl_look = QLabel()
        t_row1.addWidget(self.lbl_look)
        self.combo_look_mode = QComboBox()
        self.combo_look_mode.currentIndexChanged.connect(self._on_look_options_changed)
        t_row1.addWidget(self.combo_look_mode, 2)

        topo_layout.addLayout(t_row1)

        # Advanced GIS Row (hidden in Basic Mode)
        self.prof_adv_gis_widget = QWidget()
        adv_gis_layout = QHBoxLayout(self.prof_adv_gis_widget)
        adv_gis_layout.setContentsMargins(0, 0, 0, 0)
        adv_gis_layout.setSpacing(8)

        self.lbl_slope = QLabel()
        adv_gis_layout.addWidget(self.lbl_slope)
        self.combo_slope_layer = QComboBox()
        adv_gis_layout.addWidget(self.combo_slope_layer, 2)

        self.btn_load_slope = QPushButton()
        self.btn_load_slope.setStyleSheet("font-weight: bold; padding: 4px 8px; background-color: #fef3c7; color: #92400e; border: 1px solid #fde68a; border-radius: 4px;")
        self.btn_load_slope.clicked.connect(self._on_load_slope_file)
        adv_gis_layout.addWidget(self.btn_load_slope)

        self.lbl_kot = QLabel()
        adv_gis_layout.addWidget(self.lbl_kot)
        self.combo_contour_field = QComboBox()
        adv_gis_layout.addWidget(self.combo_contour_field, 1)

        self.lbl_floors_field = QLabel()
        adv_gis_layout.addWidget(self.lbl_floors_field)
        self.combo_bldg_field = QComboBox()
        adv_gis_layout.addWidget(self.combo_bldg_field, 1)

        self.lbl_step = QLabel()
        adv_gis_layout.addWidget(self.lbl_step)
        self.spin_step_m = QDoubleSpinBox()
        self.spin_step_m.setRange(0.5, 20.0)
        self.spin_step_m.setValue(2.0)
        self.spin_step_m.setSingleStep(0.5)
        self.spin_step_m.setSuffix(" m")
        adv_gis_layout.addWidget(self.spin_step_m)

        self.lbl_depth = QLabel()
        adv_gis_layout.addWidget(self.lbl_depth)
        self.spin_look_depth = QDoubleSpinBox()
        self.spin_look_depth.setRange(0.0, 120.0)
        self.spin_look_depth.setValue(25.0)
        self.spin_look_depth.setSingleStep(5.0)
        self.spin_look_depth.setSuffix(" m")
        self.spin_look_depth.valueChanged.connect(self._on_look_options_changed)
        adv_gis_layout.addWidget(self.spin_look_depth)

        self.lbl_roads = QLabel()
        adv_gis_layout.addWidget(self.lbl_roads)
        self.combo_road_layer = QComboBox()
        adv_gis_layout.addWidget(self.combo_road_layer, 2)

        self.chk_profile_trees = QCheckBox()
        self.chk_profile_trees.setChecked(False)
        adv_gis_layout.addWidget(self.chk_profile_trees)

        topo_layout.addWidget(self.prof_adv_gis_widget)

        # Action Row (Always visible)
        t_row_act = QHBoxLayout()
        t_row_act.setSpacing(10)

        self.btn_refresh_profile = QPushButton()
        self.btn_refresh_profile.setStyleSheet("font-weight: bold; padding: 6px 14px; background-color: #dbeafe; color: #1e40af; border: 1px solid #93c5fd; border-radius: 6px;")
        self.btn_refresh_profile.clicked.connect(self._on_refresh_profile_from_layers)
        t_row_act.addWidget(self.btn_refresh_profile, 2)

        self.btn_pick_ab_map = QPushButton()
        self.btn_pick_ab_map.setStyleSheet("""
            QPushButton {
                font-weight: bold;
                padding: 6px 16px;
                background-color: #fef08a;
                color: #854d0e;
                border: 1px solid #eab308;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #fde047;
            }
        """)
        self.btn_pick_ab_map.clicked.connect(self._on_start_map_section_tool)
        t_row_act.addWidget(self.btn_pick_ab_map, 2)

        topo_layout.addLayout(t_row_act)
        layout.addWidget(self.topo_box)

        # 3. Live Topography Badge
        self.lbl_profile_analysis = QLabel()
        self.lbl_profile_analysis.setAlignment(ALIGN_CENTER)
        self.lbl_profile_analysis.setFixedHeight(28)
        self.lbl_profile_analysis.setStyleSheet("font-size: 11px; font-weight: bold; border-radius: 6px; padding: 2px 10px; background-color: #f1f5f9; border: 1px solid #cbd5e1;")
        layout.addWidget(self.lbl_profile_analysis)

        # 4. Live 1:1000 Profile Canvas
        self.profile_canvas = UrbanProfileCanvasWidget(profile=self.current_profile)
        self.profile_canvas.buildingClicked.connect(self._on_profile_building_clicked)
        layout.addWidget(self.profile_canvas, 1)

        # 5. Manual Building/Tree Editor (Advanced Mode)
        self.prof_insp_frame = QFrame()
        self.prof_insp_frame.setStyleSheet("background-color: #ffffff; border: 1.5px solid #cbd5e1; border-radius: 8px; padding: 4px;")
        pi_layout = QHBoxLayout(self.prof_insp_frame)
        pi_layout.setContentsMargins(10, 5, 10, 5)
        pi_layout.setSpacing(10)

        self.lbl_prof_bldg = QLabel()
        pi_layout.addWidget(self.lbl_prof_bldg, 2)

        self.lbl_prof_floors = QLabel()
        pi_layout.addWidget(self.lbl_prof_floors)
        self.spin_prof_floors = QSpinBox()
        self.spin_prof_floors.setRange(1, 24)
        self.spin_prof_floors.setValue(4)
        self.spin_prof_floors.valueChanged.connect(self._on_prof_floors_changed)
        pi_layout.addWidget(self.spin_prof_floors)

        self.lbl_prof_width = QLabel()
        pi_layout.addWidget(self.lbl_prof_width)
        self.spin_prof_width = QDoubleSpinBox()
        self.spin_prof_width.setRange(5.0, 150.0)
        self.spin_prof_width.setValue(25.0)
        self.spin_prof_width.valueChanged.connect(self._on_prof_width_changed)
        pi_layout.addWidget(self.spin_prof_width)

        self.btn_add_bldg = QPushButton()
        self.btn_add_bldg.setStyleSheet("font-weight: bold; padding: 4px 10px; background-color: #ecfdf5; color: #065f46; border: 1px solid #34d399; border-radius: 4px;")
        self.btn_add_bldg.clicked.connect(self._on_add_building_to_profile)
        pi_layout.addWidget(self.btn_add_bldg)

        self.btn_del_bldg = QPushButton()
        self.btn_del_bldg.setStyleSheet("font-weight: bold; padding: 4px 10px; background-color: #fee2e2; color: #b91c1c; border: 1px solid #fca5a5; border-radius: 4px;")
        self.btn_del_bldg.clicked.connect(self._on_del_building_from_profile)
        pi_layout.addWidget(self.btn_del_bldg)

        self.btn_add_tree_cluster = QPushButton()
        self.btn_add_tree_cluster.setStyleSheet("font-weight: bold; padding: 4px 10px; background-color: #f0fdf4; color: #166534; border: 1px solid #86efac; border-radius: 4px;")
        self.btn_add_tree_cluster.clicked.connect(self._on_add_tree_cluster)
        pi_layout.addWidget(self.btn_add_tree_cluster)

        layout.addWidget(self.prof_insp_frame)

        # 6. Export Row
        prof_actions = QHBoxLayout()
        prof_actions.setSpacing(8)

        self.btn_prof_print = QPushButton()
        self.btn_prof_print.setStyleSheet("font-weight: bold; padding: 6px 14px; background-color: #fef08a; color: #854d0e; border: 1px solid #eab308; border-radius: 6px;")
        self.btn_prof_print.clicked.connect(self._on_add_profile_to_print_layout)
        prof_actions.addWidget(self.btn_prof_print)

        self.btn_prof_svg = QPushButton()
        self.btn_prof_svg.setStyleSheet("font-weight: bold; padding: 6px 14px; background-color: #ecfdf5; color: #065f46; border: 1px solid #34d399; border-radius: 6px;")
        self.btn_prof_svg.clicked.connect(self._on_export_profile_svg)
        prof_actions.addWidget(self.btn_prof_svg)

        self.btn_prof_png = QPushButton()
        self.btn_prof_png.setStyleSheet("font-weight: bold; padding: 6px 14px; background-color: #e0e7ff; color: #3730a3; border: 1px solid #818cf8; border-radius: 6px;")
        self.btn_prof_png.clicked.connect(self._on_export_profile_png)
        prof_actions.addWidget(self.btn_prof_png)

        prof_actions.addStretch()

        self.btn_prof_close = QPushButton()
        self.btn_prof_close.setStyleSheet("padding: 6px 18px; font-weight: bold; border-radius: 6px;")
        self.btn_prof_close.clicked.connect(self.accept)
        prof_actions.addWidget(self.btn_prof_close)

        layout.addLayout(prof_actions)

    # =========================================================================
    # MODE & LANGUAGE SWITCHING
    # =========================================================================

    def set_advanced_mode(self, enabled: bool):
        """Toggle between clean Basic Mode and full Advanced Studio tools."""
        self.is_advanced_mode = bool(enabled)
        self.btn_mode_basic.setChecked(not self.is_advanced_mode)
        self.btn_mode_advanced.setChecked(self.is_advanced_mode)
        self._apply_ui_mode()

    def set_ui_language(self, lang: str):
        """Switch plugin language ('en' or 'tr') without modifying any GIS/section geometry."""
        norm = set_language(lang)
        self.btn_lang_en.setChecked(norm == "en")
        self.btn_lang_tr.setChecked(norm == "tr")

        retranslate_section_inplace(self.current_section, norm)
        retranslate_profile_inplace(self.master_profile, norm)
        if self.current_profile and self.current_profile is not self.master_profile:
            retranslate_profile_inplace(self.current_profile, norm)
        for seg in getattr(self, "profile_segments", []):
            retranslate_profile_inplace(seg, norm)

        self._retranslate_ui()
        self._sync_ui_from_section()
        self._sync_ui_from_profile(keep_segment=True)

    def _apply_ui_mode(self):
        adv = self.is_advanced_mode
        self.btn_mode_basic.setStyleSheet(_PILL_IDLE if adv else _PILL_ACTIVE)
        self.btn_mode_advanced.setStyleSheet(_PILL_ACTIVE if adv else _PILL_IDLE)

        # Tab 1 Basic vs Advanced visibility
        self.lbl_road_name.setVisible(adv)
        self.txt_road_name.setVisible(adv)
        self.slider_elem_width.setVisible(adv)
        self.insp_adv_widget.setVisible(adv)
        self.btn_toggle_utilities.setVisible(adv)
        self.btn_toggle_buildings.setVisible(adv)
        self.btn_map_line.setVisible(adv)
        for btn in self._palette_adv_buttons:
            btn.setVisible(adv)
        if not adv:
            self.utility_drawer.setVisible(False)
            self.bldg_drawer.setVisible(False)

        # Tab 2 Basic vs Advanced visibility
        self.prof_top_frame.setVisible(adv)
        self.prof_adv_gis_widget.setVisible(adv)
        self.prof_insp_frame.setVisible(adv)
        self.btn_load_dem.setVisible(adv)
        self.btn_load_contour.setVisible(adv)

        self._on_topography_mode_changed(self.combo_topo_mode.currentIndex())
        self._update_segment_controls()

    def _populate_combo_preserving_data(self, combo: QComboBox, items):
        cur_data = combo.currentData()
        cur_idx = combo.currentIndex()
        combo.blockSignals(True)
        combo.clear()
        for label, data in items:
            combo.addItem(label, data)
        if cur_data is not None:
            found = combo.findData(cur_data)
            if found >= 0:
                combo.setCurrentIndex(found)
        elif 0 <= cur_idx < combo.count():
            combo.setCurrentIndex(cur_idx)
        combo.blockSignals(False)

    def _retranslate_ui(self):
        lang = get_language()
        self._updating_ui = True
        try:
            self.btn_lang_en.setStyleSheet(_PILL_ACTIVE if lang == "en" else _PILL_IDLE)
            self.btn_lang_tr.setStyleSheet(_PILL_ACTIVE if lang == "tr" else _PILL_IDLE)

            self.setWindowTitle(tr_text("window_title", lang))
            self.lbl_brand.setText(tr_text("brand_html", lang))
            self.lbl_mode.setText(tr_text("mode_label", lang))
            self.btn_mode_basic.setText(tr_text("mode_basic", lang))
            self.btn_mode_basic.setToolTip(tr_text("mode_tooltip", lang))
            self.btn_mode_advanced.setText(tr_text("mode_advanced", lang))
            self.btn_mode_advanced.setToolTip(tr_text("mode_tooltip", lang))
            self.lbl_lang.setText(tr_text("lang_label", lang))

            self.btn_minimize_drawer.setText(
                tr_text("btn_expand" if self.is_collapsed else "btn_collapse", lang)
            )
            self.lbl_mini_status.setText(tr_text("mini_pick_init", lang))
            self.lbl_mini_look.setText(tr_text("mini_look", lang))
            self.btn_mini_expand.setText(tr_text("mini_expand", lang))
            self.btn_mini_cancel.setText(tr_text("mini_cancel", lang))

            self.main_tabs.setTabText(0, tr_text("tab_street", lang))
            self.main_tabs.setTabText(1, tr_text("tab_profile", lang))

            # Tab 1 labels
            self.lbl_template.setText(f"<b>{tr_text('lbl_template', lang)}</b>")
            self.lbl_road_name.setText(f"<b>{tr_text('lbl_road_name', lang)}</b>")
            self.lbl_corridor_width.setText(f"<b>{tr_text('lbl_corridor_width', lang)}</b>")
            self.lbl_theme.setText(f"<b>{tr_text('lbl_theme', lang)}</b>")
            self.btn_select_map.setText(tr_text("btn_read_map_road", lang))

            self._populate_combo_preserving_data(self.combo_visual_theme, [
                (tr_text("theme_architectural", lang), "architectural"),
                (tr_text("theme_technical_cad", lang), "technical_cad"),
                (tr_text("theme_sunset_warm", lang), "sunset_warm"),
                (tr_text("theme_night_lighting", lang), "night_lighting"),
            ])
            self._populate_presets()

            self.btn_move_left.setText(tr_text("btn_move_left", lang))
            self.btn_move_right.setText(tr_text("btn_move_right", lang))
            self.btn_del_elem.setText(tr_text("btn_delete", lang))

            self.chk_trees.setText(tr_text("chk_trees", lang))
            self.chk_lighting.setText(tr_text("chk_lighting", lang))
            self.chk_bench.setText(tr_text("chk_bench", lang))
            self.chk_bus_shelter.setText(tr_text("chk_bus_shelter", lang))
            self.chk_tactile.setText(tr_text("chk_tactile", lang))
            self.chk_bike_rack.setText(tr_text("chk_bike_rack", lang))
            self.lbl_vehicle.setText(tr_text("lbl_vehicle", lang))
            self.lbl_people.setText(tr_text("lbl_people", lang))

            veh_idx = self.combo_vehicle.currentIndex()
            self.combo_vehicle.blockSignals(True)
            self.combo_vehicle.clear()
            self.combo_vehicle.addItems([
                tr_text("veh_none", lang),
                tr_text("veh_car", lang),
                tr_text("veh_bus", lang),
            ])
            if 0 <= veh_idx < 3:
                self.combo_vehicle.setCurrentIndex(veh_idx)
            self.combo_vehicle.blockSignals(False)

            self.lbl_add_strip.setText(tr_text("lbl_add_strip", lang))
            self.btn_toggle_utilities.setText(
                tr_text("btn_utilities_hide" if self.utility_drawer.isVisible() else "btn_utilities_show", lang)
            )
            self.btn_toggle_buildings.setText(
                tr_text("btn_buildings_hide" if self.bldg_drawer.isVisible() else "btn_buildings_show", lang)
            )
            for btn, key in self._palette_buttons:
                btn.setText(tr_text(key, lang))

            self.lbl_utilities.setText(tr_text("lbl_utilities", lang))
            self.chk_util_water.setText(tr_text("chk_util_water", lang))
            self.chk_util_telecom.setText(tr_text("chk_util_telecom", lang))
            self.chk_util_power.setText(tr_text("chk_util_power", lang))
            self.chk_util_gas.setText(tr_text("chk_util_gas", lang))
            self.chk_util_drainage.setText(tr_text("chk_util_drainage", lang))
            self.chk_util_sewer.setText(tr_text("chk_util_sewer", lang))
            self.chk_util_gallery.setText(tr_text("chk_util_gallery", lang))
            self.chk_util_gallery.setToolTip(tr_text("tip_util_gallery", lang))
            self.btn_util_all.setText(tr_text("btn_util_all", lang))
            self.btn_util_none.setText(tr_text("btn_util_none", lang))
            self.lbl_visual_layers.setText(tr_text("lbl_visual_layers", lang))
            self.chk_show_subgrade.setText(tr_text("chk_show_subgrade", lang))
            self.chk_show_buildings.setText(tr_text("chk_show_buildings", lang))
            self.chk_show_slopes.setText(tr_text("chk_show_slopes", lang))
            self.chk_show_cards.setText(tr_text("chk_show_cards", lang))
            self.chk_show_dimensions.setText(tr_text("chk_show_dimensions", lang))

            self.lbl_left_floors.setText(tr_text("lbl_left_floors", lang))
            self.lbl_right_floors.setText(tr_text("lbl_right_floors", lang))
            self.lbl_left_setback.setText(tr_text("lbl_setback", lang))
            self.lbl_right_setback.setText(tr_text("lbl_setback", lang))
            self.lbl_left_sign.setText(tr_text("lbl_sign", lang))
            self.lbl_right_sign.setText(tr_text("lbl_sign", lang))

            self.btn_map_line.setText(tr_text("btn_map_line", lang))
            self.btn_print_layout.setText(tr_text("btn_print_layout", lang))
            self.btn_export_svg.setText(tr_text("btn_export_svg", lang))
            self.btn_export_png.setText(tr_text("btn_export_png", lang))
            self.btn_close.setText(tr_text("btn_close", lang))

            # Tab 2 labels
            self.lbl_profile_preset.setText(tr_text("lbl_profile_preset", lang))
            self._populate_combo_preserving_data(self.combo_profile_presets, [
                (tr_text("prof_preset_aa", lang), "preset_aa"),
                (tr_text("prof_preset_bb", lang), "preset_bb"),
            ])
            self.lbl_profile_title.setText(tr_text("lbl_title", lang))
            self.lbl_sky.setText(tr_text("lbl_sky", lang))
            self._populate_combo_preserving_data(self.combo_sky, [
                (tr_text("sky_sunset", lang), "sunset"),
                (tr_text("sky_golden_hour", lang), "golden_hour"),
                (tr_text("sky_daylight", lang), "daylight"),
            ])
            self.lbl_exag.setText(tr_text("lbl_exag", lang))
            self._populate_combo_preserving_data(self.combo_exag, [
                (tr_text("exag_1", lang), 1.0),
                (tr_text("exag_2", lang), 2.0),
                (tr_text("exag_3", lang), 3.0),
                (tr_text("exag_5", lang), 5.0),
                (tr_text("exag_10", lang), 10.0),
            ])
            self.lbl_segment.setText(tr_text("lbl_segment", lang))
            self.btn_prev_segment.setText(tr_text("btn_prev_seg", lang))
            self.btn_next_segment.setText(tr_text("btn_next_seg", lang))
            self.btn_export_all_segments.setText(tr_text("btn_export_all_segs", lang))

            self.topo_box.setTitle(tr_text("box_topo_title", lang))
            self.lbl_source_mode.setText(tr_text("lbl_source_mode", lang))
            self._populate_combo_preserving_data(self.combo_topo_mode, [
                (tr_text("mode_dem", lang), "dem"),
                (tr_text("mode_contours", lang), "contours"),
                (tr_text("mode_dem_slope", lang), "dem_slope"),
                (tr_text("mode_preset", lang), "preset"),
            ])
            self.lbl_dem.setText(tr_text("lbl_terrain_layer" if not self.is_advanced_mode else "lbl_dem", lang))
            self.btn_load_dem.setText(tr_text("btn_load_dem", lang))
            self.lbl_contour.setText(tr_text("lbl_contour", lang))
            self.btn_load_contour.setText(tr_text("btn_load_contour", lang))
            self.lbl_bldg_layer.setText(tr_text("lbl_bldg_layer", lang))
            self.lbl_look.setText(tr_text("lbl_look", lang))
            self._populate_combo_preserving_data(self.combo_look_mode, [
                (tr_text("look_auto", lang), "auto"),
                (tr_text("look_left", lang), "left"),
                (tr_text("look_right", lang), "right"),
                (tr_text("look_both", lang), "both"),
                (tr_text("look_cut_only", lang), "cut_only"),
            ])
            self._populate_combo_preserving_data(self.combo_mini_look, [
                (tr_text("mini_look_auto", lang), "auto"),
                (tr_text("mini_look_left", lang), "left"),
                (tr_text("mini_look_right", lang), "right"),
                (tr_text("mini_look_both", lang), "both"),
                (tr_text("mini_look_cut_only", lang), "cut_only"),
            ])

            self.lbl_slope.setText(tr_text("lbl_slope", lang))
            self.btn_load_slope.setText(tr_text("btn_load_slope", lang))
            self.lbl_kot.setText(tr_text("lbl_elev_field", lang))
            self.lbl_floors_field.setText(tr_text("lbl_floors_field", lang))
            self.lbl_step.setText(tr_text("lbl_step", lang))
            self.lbl_depth.setText(tr_text("lbl_depth", lang))
            self.lbl_roads.setText(tr_text("lbl_roads", lang))
            self.chk_profile_trees.setText(tr_text("chk_sample_trees", lang))

            self.btn_refresh_profile.setText(tr_text("btn_refresh_profile", lang))
            self.btn_pick_ab_map.setText(tr_text("btn_pick_ab_map", lang))

            if self.combo_bldg_layer.count() > 0:
                self.combo_bldg_layer.setItemText(0, tr_text("item_none_bldg", lang))
            if self.combo_slope_layer.count() > 0:
                self.combo_slope_layer.setItemText(0, tr_text("item_none_slope", lang))
            if self.combo_road_layer.count() > 0:
                self.combo_road_layer.setItemText(0, tr_text("item_none_road", lang))

            self.lbl_prof_bldg.setText(tr_text("mass_info_none", lang))
            self.lbl_prof_floors.setText(tr_text("lbl_floors", lang))
            self.lbl_prof_width.setText(tr_text("lbl_width_m", lang))
            self.btn_add_bldg.setText(tr_text("btn_add_mass", lang))
            self.btn_del_bldg.setText(tr_text("btn_del_mass", lang))
            self.btn_add_tree_cluster.setText(tr_text("btn_add_trees", lang))

            self.btn_prof_print.setText(tr_text("btn_prof_print", lang))
            self.btn_prof_svg.setText(tr_text("btn_prof_svg", lang))
            self.btn_prof_png.setText(tr_text("btn_prof_png", lang))
            self.btn_prof_close.setText(tr_text("btn_close", lang))
        finally:
            self._updating_ui = False

    # =========================================================================
    # TAB 1 HANDLERS (STREET CROSS-SECTION)
    # =========================================================================

    def _populate_presets(self):
        lang = get_language()
        cur_id = self.combo_presets.currentData() or "15m"
        self.combo_presets.blockSignals(True)
        self.combo_presets.clear()
        presets = list_presets(lang=lang)
        default_idx = 0
        for i, p in enumerate(presets):
            self.combo_presets.addItem(f"{p['name']} ({p['right_of_way']:.1f} m)", p["id"])
            if p["id"] == cur_id:
                default_idx = i
        self.combo_presets.setCurrentIndex(default_idx)
        self.combo_presets.blockSignals(False)

    def _on_preset_changed(self, idx):
        if self._updating_ui:
            return
        pid = self.combo_presets.itemData(idx)
        if pid:
            prev_sec = self.current_section
            new_sec = get_preset_by_id(pid, lang=get_language())
            if prev_sec:
                for attr in (
                    "show_subgrade",
                    "show_utilities",
                    "has_water_pipe",
                    "has_telecom_pipe",
                    "has_power_cable",
                    "has_gas_pipe",
                    "has_drainage_pipe",
                    "has_sewer_pipe",
                    "has_utility_gallery",
                    "visual_theme",
                    "show_buildings",
                    "show_dimensions",
                    "show_cards",
                    "show_slope_arrows",
                ):
                    if hasattr(prev_sec, attr):
                        setattr(new_sec, attr, getattr(prev_sec, attr))
            self.current_section = new_sec
            self.txt_road_name.blockSignals(True)
            self.txt_road_name.setText(self.current_section.name)
            self.txt_road_name.blockSignals(False)

            self.spin_row.blockSignals(True)
            self.spin_row.setValue(self.current_section.right_of_way)
            self.spin_row.blockSignals(False)

            self.canvas.selected_element_idx = 0
            self._sync_ui_from_section()

    def _on_road_name_changed(self, text):
        self.current_section.name = text
        self.canvas.update()

    def _on_row_width_changed(self, val):
        self.current_section.right_of_way = float(val)
        self._update_status_banner()
        self.canvas.update()

    def _toggle_utilities_drawer(self):
        lang = get_language()
        is_vis = self.utility_drawer.isVisible()
        self.utility_drawer.setVisible(not is_vis)
        self.btn_toggle_utilities.setText(
            tr_text("btn_utilities_hide" if not is_vis else "btn_utilities_show", lang)
        )

    def _toggle_buildings_drawer(self):
        lang = get_language()
        is_vis = self.bldg_drawer.isVisible()
        self.bldg_drawer.setVisible(not is_vis)
        self.btn_toggle_buildings.setText(
            tr_text("btn_buildings_hide" if not is_vis else "btn_buildings_show", lang)
        )

    def _on_visual_theme_changed(self, idx):
        if self._updating_ui:
            return
        theme = self.combo_visual_theme.itemData(idx) or "architectural"
        self.current_section.visual_theme = theme
        self.canvas.update()

    def _on_utilities_changed(self):
        if self._updating_ui:
            return
        sec = self.current_section
        sec.has_water_pipe = self.chk_util_water.isChecked()
        sec.has_telecom_pipe = self.chk_util_telecom.isChecked()
        sec.has_power_cable = self.chk_util_power.isChecked()
        sec.has_gas_pipe = self.chk_util_gas.isChecked()
        sec.has_drainage_pipe = self.chk_util_drainage.isChecked()
        sec.has_sewer_pipe = self.chk_util_sewer.isChecked()
        sec.has_utility_gallery = self.chk_util_gallery.isChecked()
        sec.show_utilities = any([
            sec.has_water_pipe,
            sec.has_telecom_pipe,
            sec.has_power_cable,
            sec.has_gas_pipe,
            sec.has_drainage_pipe,
            sec.has_sewer_pipe,
            sec.has_utility_gallery,
        ])
        self.canvas.update()

    def _set_all_utilities(self, state: bool):
        self._updating_ui = True
        self.chk_util_water.setChecked(state)
        self.chk_util_telecom.setChecked(state)
        self.chk_util_power.setChecked(state)
        self.chk_util_gas.setChecked(state)
        self.chk_util_drainage.setChecked(state)
        self.chk_util_sewer.setChecked(state)
        if not state:
            self.chk_util_gallery.setChecked(False)
        self._updating_ui = False
        self._on_utilities_changed()

    def _on_visual_options_changed(self):
        if self._updating_ui:
            return
        sec = self.current_section
        sec.show_subgrade = self.chk_show_subgrade.isChecked()
        sec.show_buildings = self.chk_show_buildings.isChecked()
        sec.show_slope_arrows = self.chk_show_slopes.isChecked()
        sec.show_cards = self.chk_show_cards.isChecked()
        sec.show_dimensions = self.chk_show_dimensions.isChecked()
        self.canvas.update()

    def _on_canvas_utility_toggled(self, _u_key: str):
        self._sync_ui_from_section()

    def _sync_ui_from_section(self):
        self._updating_ui = True
        try:
            sec = self.current_section
            sel_idx = max(0, min(self.canvas.selected_element_idx, len(sec.elements) - 1))
            self.canvas.set_section(sec)
            self.canvas.set_selected_element(sel_idx)

            self._load_element_properties(sel_idx)
            self._update_status_banner()

            self.txt_road_name.setText(sec.name)

            lb = sec.left_building
            self.spin_left_floors.setValue(lb.floors)
            self.spin_left_setback.setValue(lb.setback)
            self.txt_left_shop.setText(lb.shop_name)

            rb = sec.right_building
            self.spin_right_floors.setValue(rb.floors)
            self.spin_right_setback.setValue(rb.setback)
            self.txt_right_shop.setText(rb.shop_name)

            self.chk_util_water.setChecked(getattr(sec, "has_water_pipe", True))
            self.chk_util_telecom.setChecked(getattr(sec, "has_telecom_pipe", True))
            self.chk_util_power.setChecked(getattr(sec, "has_power_cable", True))
            self.chk_util_gas.setChecked(getattr(sec, "has_gas_pipe", True))
            self.chk_util_drainage.setChecked(getattr(sec, "has_drainage_pipe", True))
            self.chk_util_sewer.setChecked(getattr(sec, "has_sewer_pipe", False))
            self.chk_util_gallery.setChecked(getattr(sec, "has_utility_gallery", False))

            self.chk_show_subgrade.setChecked(getattr(sec, "show_subgrade", True))
            self.chk_show_buildings.setChecked(getattr(sec, "show_buildings", True))
            self.chk_show_slopes.setChecked(getattr(sec, "show_slope_arrows", True))
            self.chk_show_cards.setChecked(getattr(sec, "show_cards", True))
            self.chk_show_dimensions.setChecked(getattr(sec, "show_dimensions", True))

            t_idx = self.combo_visual_theme.findData(getattr(sec, "visual_theme", "architectural"))
            if t_idx >= 0:
                self.combo_visual_theme.setCurrentIndex(t_idx)
        finally:
            self._updating_ui = False

    def _load_element_properties(self, idx):
        if not (0 <= idx < len(self.current_section.elements)):
            return
        lang = get_language()
        elem = self.current_section.elements[idx]
        self.lbl_selected_title.setText(
            f"<b>{tr_text('lbl_selected_prefix', lang)}</b> "
            f"<span style='color: #2563eb;'>#{idx + 1} {elem.label}</span> "
            f"<span style='color: #64748b; font-size: 11px;'>({elem.width:.2f} m)</span>"
        )
        self.spin_elem_width.blockSignals(True)
        self.spin_elem_width.setValue(elem.width)
        self.spin_elem_width.blockSignals(False)

        self.slider_elem_width.blockSignals(True)
        self.slider_elem_width.setValue(int(elem.width * 100))
        self.slider_elem_width.blockSignals(False)

        self.chk_trees.blockSignals(True)
        self.chk_trees.setChecked(elem.has_trees)
        self.chk_trees.blockSignals(False)

        self.chk_lighting.blockSignals(True)
        self.chk_lighting.setChecked(elem.has_lighting)
        self.chk_lighting.blockSignals(False)

        self.chk_bench.blockSignals(True)
        self.chk_bench.setChecked(elem.has_bench)
        self.chk_bench.blockSignals(False)

        self.chk_tactile.blockSignals(True)
        self.chk_tactile.setChecked(elem.has_tactile)
        self.chk_tactile.blockSignals(False)

        self.chk_bus_shelter.blockSignals(True)
        self.chk_bus_shelter.setChecked(elem.has_bus_shelter)
        self.chk_bus_shelter.blockSignals(False)

        self.chk_bike_rack.blockSignals(True)
        self.chk_bike_rack.setChecked(elem.has_bike_rack)
        self.chk_bike_rack.blockSignals(False)

        self.combo_vehicle.blockSignals(True)
        self.combo_vehicle.setCurrentIndex(1 if elem.vehicle_type == "car" else 2 if elem.vehicle_type == "bus" else 0)
        self.combo_vehicle.blockSignals(False)

        self.spin_pedestrians.blockSignals(True)
        self.spin_pedestrians.setValue(elem.pedestrian_count)
        self.spin_pedestrians.blockSignals(False)

    def _update_status_banner(self):
        lang = get_language()
        sec = self.current_section
        stats = sec.summary_stats()
        diff = sec.width_difference
        if abs(diff) < 0.05:
            text = tr_text(
                "status_balanced",
                lang,
                tot=sec.total_width,
                row=sec.right_of_way,
                ped=stats["pedestrian_pct"],
                veh=stats["vehicular_pct"],
                cyc=stats["cycling_pct"],
            )
            style = "background-color: #dcfce7; color: #166534; font-weight: bold; border: 1.5px solid #86efac; border-radius: 6px; padding: 4px 12px;"
        elif diff > 0:
            text = tr_text("status_narrow", lang, row=sec.right_of_way, tot=sec.total_width, diff=diff)
            style = "background-color: #fef9c3; color: #854d0e; font-weight: bold; border: 1.5px solid #fde047; border-radius: 6px; padding: 4px 12px;"
        else:
            text = tr_text("status_over", lang, row=sec.right_of_way, tot=sec.total_width, over=abs(diff))
            style = "background-color: #fee2e2; color: #991b1b; font-weight: bold; border: 1.5px solid #fca5a5; border-radius: 6px; padding: 4px 12px;"
        self.lbl_status.setText(text)
        self.lbl_status.setStyleSheet(style)

    def _on_canvas_element_clicked(self, idx):
        self._load_element_properties(idx)

    def _on_canvas_width_adjusted(self, idx, delta):
        if not (0 <= idx < len(self.current_section.elements)):
            return
        elem = self.current_section.elements[idx]
        elem.width = round(max(0.25, min(30.0, elem.width + delta)), 2)
        self.canvas.set_selected_element(idx)
        self._sync_ui_from_section()

    def _on_canvas_delete_requested(self, idx):
        lang = get_language()
        if len(self.current_section.elements) <= 1:
            QMessageBox.warning(self, tr_text("msg_warn", lang), tr_text("msg_min_one_elem", lang))
            return
        self.current_section.remove_element(idx)
        self.canvas.selected_element_idx = max(0, idx - 1)
        self._sync_ui_from_section()

    def _adjust_selected_width(self, delta):
        self._on_canvas_width_adjusted(self.canvas.selected_element_idx, delta)

    def _on_elem_width_spin_changed(self, val):
        if self._updating_ui:
            return
        idx = self.canvas.selected_element_idx
        if 0 <= idx < len(self.current_section.elements):
            self.current_section.update_element(idx, width=float(val))
            self.slider_elem_width.blockSignals(True)
            self.slider_elem_width.setValue(int(float(val) * 100))
            self.slider_elem_width.blockSignals(False)
            self._update_status_banner()
            self.canvas.update()

    def _on_slider_width_changed(self, val_cm):
        if self._updating_ui:
            return
        val_m = val_cm / 100.0
        self.spin_elem_width.blockSignals(True)
        self.spin_elem_width.setValue(val_m)
        self.spin_elem_width.blockSignals(False)
        idx = self.canvas.selected_element_idx
        if 0 <= idx < len(self.current_section.elements):
            self.current_section.update_element(idx, width=val_m)
            self._update_status_banner()
            self.canvas.update()

    def _quick_add_element(self, elem_type, width, label=None, **kwargs):
        new_elem = SectionElement(element_type=elem_type, width=width, label=label or "", **kwargs)
        cur_idx = self.canvas.selected_element_idx
        insert_idx = cur_idx + 1 if cur_idx >= 0 else len(self.current_section.elements)
        self.current_section.add_element(new_elem, index=insert_idx)
        self.canvas.selected_element_idx = insert_idx
        self._sync_ui_from_section()

    def _on_move_element_left(self):
        idx = self.canvas.selected_element_idx
        if idx > 0:
            self.current_section.move_element(idx, idx - 1)
            self.canvas.selected_element_idx = idx - 1
            self._sync_ui_from_section()

    def _on_move_element_right(self):
        idx = self.canvas.selected_element_idx
        if idx < len(self.current_section.elements) - 1:
            self.current_section.move_element(idx, idx + 1)
            self.canvas.selected_element_idx = idx + 1
            self._sync_ui_from_section()

    def _on_delete_element(self):
        self._on_canvas_delete_requested(self.canvas.selected_element_idx)

    def _on_tree_toggled(self, val):
        idx = self.canvas.selected_element_idx
        if 0 <= idx < len(self.current_section.elements):
            self.current_section.update_element(idx, has_trees=bool(val))
            self.canvas.update()

    def _on_lighting_toggled(self, val):
        idx = self.canvas.selected_element_idx
        if 0 <= idx < len(self.current_section.elements):
            self.current_section.update_element(idx, has_lighting=bool(val))
            self.canvas.update()

    def _on_bench_toggled(self, val):
        idx = self.canvas.selected_element_idx
        if 0 <= idx < len(self.current_section.elements):
            self.current_section.update_element(idx, has_bench=bool(val))
            self.canvas.update()

    def _on_tactile_toggled(self, val):
        idx = self.canvas.selected_element_idx
        if 0 <= idx < len(self.current_section.elements):
            self.current_section.update_element(idx, has_tactile=bool(val))
            self.canvas.update()

    def _on_bus_shelter_toggled(self, val):
        idx = self.canvas.selected_element_idx
        if 0 <= idx < len(self.current_section.elements):
            self.current_section.update_element(idx, has_bus_shelter=bool(val))
            self.canvas.update()

    def _on_bike_rack_toggled(self, val):
        idx = self.canvas.selected_element_idx
        if 0 <= idx < len(self.current_section.elements):
            self.current_section.update_element(idx, has_bike_rack=bool(val))
            self.canvas.update()

    def _on_vehicle_combo_changed(self, c_idx):
        idx = self.canvas.selected_element_idx
        if 0 <= idx < len(self.current_section.elements):
            elem = self.current_section.elements[idx]
            elem.vehicle_type = "car" if c_idx == 1 else "bus" if c_idx == 2 else None
            self.canvas.update()

    def _on_pedestrians_spin_changed(self, val):
        idx = self.canvas.selected_element_idx
        if 0 <= idx < len(self.current_section.elements):
            self.current_section.update_element(idx, pedestrian_count=int(val))
            self.canvas.update()

    def _on_building_changed(self):
        if self._updating_ui:
            return
        sec = self.current_section
        sec.left_building.floors = self.spin_left_floors.value()
        sec.left_building.setback = self.spin_left_setback.value()
        sec.left_building.shop_name = self.txt_left_shop.text()

        sec.right_building.floors = self.spin_right_floors.value()
        sec.right_building.setback = self.spin_right_setback.value()
        sec.right_building.shop_name = self.txt_right_shop.text()
        self.canvas.update()

    def _on_read_selected_road(self):
        lang = get_language()
        layers = get_road_line_layers()
        if not layers:
            QMessageBox.information(self, tr_text("msg_info", lang), tr_text("msg_no_road_layer", lang))
            return

        active_layer = self.iface.activeLayer() if self.iface else layers[0]
        if not active_layer or active_layer not in layers:
            active_layer = layers[0]

        info = extract_selected_road_info(active_layer)
        if not info:
            QMessageBox.warning(
                self,
                tr_text("msg_warn", lang),
                tr_text("msg_no_sel_road", lang, name=active_layer.name()),
            )
            return

        self.selected_road_geom = info["geometry"]
        self.selected_road_name = info["name"]
        self.txt_road_name.setText(self.selected_road_name)

        if info["width"]:
            w = info["width"]
            self.current_section = get_preset_by_width(w, lang=lang)
            self.current_section.name = f"{self.selected_road_name} ({w:.1f} m)"
            self.spin_row.setValue(w)
            self._sync_ui_from_section()
            QMessageBox.information(
                self,
                tr_text("msg_info", lang),
                tr_text("msg_road_loaded", lang, name=self.selected_road_name, w=w),
            )

    def _on_add_map_line(self):
        lang = get_language()
        if not self.selected_road_geom:
            layers = get_road_line_layers()
            if layers:
                for f in layers[0].getFeatures():
                    if f.geometry() and not f.geometry().isEmpty():
                        self.selected_road_geom = f.geometry()
                        break
        if not self.selected_road_geom:
            QMessageBox.warning(self, tr_text("msg_warn", lang), tr_text("msg_no_road_geom", lang))
            return

        feat = add_cross_section_to_map(
            road_geometry=self.selected_road_geom,
            right_of_way=self.current_section.right_of_way,
            label="A - A'",
            road_name=self.selected_road_name,
        )
        if feat:
            QMessageBox.information(self, tr_text("msg_info", lang), tr_text("msg_line_added", lang))

    def _on_add_to_print_layout(self):
        lang = get_language()
        tmp_dir = os.path.join(QgsProject.instance().homePath() or os.path.expanduser("~"), "output")
        os.makedirs(tmp_dir, exist_ok=True)
        tmp_svg = os.path.join(tmp_dir, "urban_cross_section_layout.svg")
        SvgCrossSectionExporter(self.current_section).save_to_file(tmp_svg)
        layout_name = "Kentsel Kesitler Paftası" if lang == "tr" else "Urban Cross-Sections Layout"
        try:
            insert_section_image_to_layout(image_path=tmp_svg, layout_name=layout_name)
            QMessageBox.information(self, tr_text("msg_info", lang), tr_text("msg_layout_added", lang, path=tmp_svg))
        except Exception as e:
            QMessageBox.critical(self, tr_text("msg_error", lang), str(e))

    def _on_export_svg(self):
        lang = get_language()
        fn, _ = QFileDialog.getSaveFileName(
            self,
            tr_text("file_dlg_svg", lang),
            f"{self.current_section.name.replace(' ', '_')}.svg",
            "SVG (*.svg)",
        )
        if fn:
            SvgCrossSectionExporter(self.current_section).save_to_file(fn)
            QMessageBox.information(self, tr_text("msg_info", lang), tr_text("msg_saved", lang, path=fn))

    def _on_export_png(self):
        lang = get_language()
        fn, _ = QFileDialog.getSaveFileName(
            self,
            tr_text("file_dlg_png", lang),
            f"{self.current_section.name.replace(' ', '_')}.png",
            "PNG (*.png)",
        )
        if fn:
            self.canvas.export_to_image(fn, dpi=300)
            QMessageBox.information(self, tr_text("msg_info", lang), tr_text("msg_saved", lang, path=fn))

    # =========================================================================
    # TAB 2 HANDLERS (1:1000 URBAN PROFILE)
    # =========================================================================

    def _sync_ui_from_profile(self, keep_segment=False):
        if not hasattr(self, "master_profile") or self.master_profile is None or not keep_segment:
            self.master_profile = self.current_profile

        self.profile_canvas.set_profile(self.current_profile)
        self.txt_profile_title.blockSignals(True)
        self.txt_profile_title.setText(self.current_profile.title)
        self.txt_profile_title.blockSignals(False)
        self._update_profile_analysis_banner()
        self._update_segment_controls()

    def _update_segment_controls(self):
        if not hasattr(self, "combo_segment"):
            return
        lang = get_language()
        self.combo_segment.blockSignals(True)
        self.combo_segment.clear()

        m_prof = getattr(self, "master_profile", self.current_profile)
        tot_l = m_prof.total_length

        if tot_l > 700.0:
            self.segment_box.setVisible(True)
            self.profile_segments = m_prof.get_segments(segment_length=700.0)
            n_segs = len(self.profile_segments)

            self.combo_segment.addItem(tr_text("seg_overview", lang, len=tot_l), 0)
            for i, seg in enumerate(self.profile_segments):
                s_dist = int(i * (tot_l / n_segs))
                e_dist = int(min(tot_l, (i + 1) * (tot_l / n_segs)))
                self.combo_segment.addItem(
                    tr_text("seg_item", lang, idx=i + 1, total=n_segs, s=s_dist, e=e_dist, cnt=len(seg.buildings)),
                    i + 1,
                )

            cur_idx = 0
            for i, seg in enumerate(self.profile_segments):
                if self.current_profile == seg:
                    cur_idx = i + 1
                    break
            self.combo_segment.setCurrentIndex(cur_idx)
            self.btn_prev_segment.setEnabled(cur_idx > 0)
            self.btn_next_segment.setEnabled(cur_idx < n_segs)
        else:
            self.profile_segments = []
            self.segment_box.setVisible(self.is_advanced_mode)
            self.combo_segment.addItem(tr_text("seg_single", lang, len=tot_l), 0)
            self.btn_prev_segment.setEnabled(False)
            self.btn_next_segment.setEnabled(False)
        self.combo_segment.blockSignals(False)

    def _on_segment_changed(self, idx):
        if idx == 0:
            self.current_profile = self.master_profile
        elif hasattr(self, "profile_segments") and 1 <= idx <= len(self.profile_segments):
            self.current_profile = self.profile_segments[idx - 1]

        self.profile_canvas.set_profile(self.current_profile)
        self.txt_profile_title.blockSignals(True)
        self.txt_profile_title.setText(self.current_profile.title)
        self.txt_profile_title.blockSignals(False)
        self._update_profile_analysis_banner()

        n_segs = len(getattr(self, "profile_segments", []))
        self.btn_prev_segment.setEnabled(idx > 0)
        self.btn_next_segment.setEnabled(idx < n_segs)

    def _on_prev_segment_clicked(self):
        cur = self.combo_segment.currentIndex()
        if cur > 0:
            self.combo_segment.setCurrentIndex(cur - 1)

    def _on_next_segment_clicked(self):
        cur = self.combo_segment.currentIndex()
        if cur < self.combo_segment.count() - 1:
            self.combo_segment.setCurrentIndex(cur + 1)

    def _on_export_all_segments(self):
        lang = get_language()
        m_prof = getattr(self, "master_profile", self.current_profile)
        segs = getattr(self, "profile_segments", []) or [m_prof]

        folder = QFileDialog.getExistingDirectory(
            self,
            tr_text("file_dlg_folder", lang),
            os.path.expanduser("~"),
        )
        if not folder:
            return

        os.makedirs(folder, exist_ok=True)
        count = 0
        macro_svg = os.path.join(folder, "00_Corridor_Overview.svg")
        SvgUrbanProfileExporter(m_prof).save_to_file(macro_svg)
        count += 1

        for i, seg in enumerate(segs):
            seg_svg = os.path.join(folder, f"Sheet_{i + 1:02d}_1000_Section.svg")
            SvgUrbanProfileExporter(seg).save_to_file(seg_svg, width_px=1600, height_px=450)
            count += 1

        QMessageBox.information(
            self,
            tr_text("msg_info", lang),
            tr_text("msg_multi_saved", lang, n=count, folder=folder),
        )

    def _refresh_topography_layers(self):
        lang = get_language()
        proj = QgsProject.instance()

        self.combo_dem_layer.blockSignals(True)
        self.combo_slope_layer.blockSignals(True)
        self.combo_dem_layer.clear()
        self.combo_slope_layer.clear()
        self.combo_slope_layer.addItem(tr_text("item_none_slope", lang), None)

        rasters = [
            lyr for lyr in proj.mapLayers().values()
            if isinstance(lyr, QgsRasterLayer) and lyr.isValid()
        ]
        for r in rasters:
            self.combo_dem_layer.addItem(r.name(), r.id())
            self.combo_slope_layer.addItem(r.name(), r.id())

        dem_cand = find_dem_raster_layer()
        if dem_cand:
            idx = self.combo_dem_layer.findData(dem_cand.id())
            if idx >= 0:
                self.combo_dem_layer.setCurrentIndex(idx)

        slope_cand = find_slope_raster_layer()
        if slope_cand:
            idx = self.combo_slope_layer.findData(slope_cand.id())
            if idx >= 0:
                self.combo_slope_layer.setCurrentIndex(idx)

        self.combo_dem_layer.blockSignals(False)
        self.combo_slope_layer.blockSignals(False)

        self.combo_contour_layer.blockSignals(True)
        self.combo_contour_layer.clear()
        lines = [
            lyr for lyr in proj.mapLayers().values()
            if isinstance(lyr, QgsVectorLayer) and lyr.isValid() and lyr.geometryType() == QgsWkbTypes.GeometryType.LineGeometry
        ]
        for vl in lines:
            self.combo_contour_layer.addItem(vl.name(), vl.id())

        cnt_cand = find_contour_vector_layer()
        if cnt_cand:
            idx = self.combo_contour_layer.findData(cnt_cand.id())
            if idx >= 0:
                self.combo_contour_layer.setCurrentIndex(idx)

        self.combo_contour_layer.blockSignals(False)
        self._update_contour_fields()

        self.combo_bldg_layer.blockSignals(True)
        self.combo_bldg_layer.clear()
        self.combo_bldg_layer.addItem(tr_text("item_none_bldg", lang), None)
        polys = [
            lyr for lyr in proj.mapLayers().values()
            if isinstance(lyr, QgsVectorLayer) and lyr.isValid() and lyr.geometryType() == QgsWkbTypes.GeometryType.PolygonGeometry
        ]
        for pl in polys:
            self.combo_bldg_layer.addItem(pl.name(), pl.id())

        bldg_cand = find_building_polygon_layer()
        if bldg_cand:
            idx = self.combo_bldg_layer.findData(bldg_cand.id())
            if idx >= 0:
                self.combo_bldg_layer.setCurrentIndex(idx)

        self.combo_bldg_layer.blockSignals(False)
        self._update_bldg_fields()

        self.combo_road_layer.blockSignals(True)
        self.combo_road_layer.clear()
        self.combo_road_layer.addItem(tr_text("item_none_road", lang), None)
        for rl in lines:
            self.combo_road_layer.addItem(rl.name(), rl.id())

        road_cand = find_road_layer()
        if road_cand:
            idx = self.combo_road_layer.findData(road_cand.id())
            if idx >= 0:
                self.combo_road_layer.setCurrentIndex(idx)

        self.combo_road_layer.blockSignals(False)
        self._on_topography_mode_changed(self.combo_topo_mode.currentIndex())

    def _on_mini_look_changed(self, _idx):
        if self._updating_ui:
            return
        mode = self.combo_mini_look.currentData() or "auto"
        self.combo_look_mode.blockSignals(True)
        idx = self.combo_look_mode.findData(mode)
        if idx >= 0:
            self.combo_look_mode.setCurrentIndex(idx)
        self.combo_look_mode.blockSignals(False)
        self._apply_look_options()

    def _on_look_options_changed(self, *_args):
        if self._updating_ui:
            return
        mode = self.combo_look_mode.currentData() or "auto"
        self.combo_mini_look.blockSignals(True)
        idx = self.combo_mini_look.findData(mode)
        if idx >= 0:
            self.combo_mini_look.setCurrentIndex(idx)
        self.combo_mini_look.blockSignals(False)
        self._apply_look_options()

    def _apply_look_options(self):
        mode = self.combo_look_mode.currentData() or "auto"
        depth = self.spin_look_depth.value()
        self.spin_look_depth.setEnabled(mode != "cut_only")
        if self.map_tool_section is not None:
            self.map_tool_section.set_look_options(mode, depth)

    def _on_topography_mode_changed(self, idx):
        lang = get_language()
        mode = self.combo_topo_mode.itemData(idx) or "dem"
        is_dem = (mode in ("dem", "dem_slope"))
        is_slope = (mode == "dem_slope")
        is_contour = (mode == "contours")
        adv = self.is_advanced_mode

        if adv:
            self.lbl_dem.setVisible(True)
            self.lbl_dem.setText(tr_text("lbl_dem", lang))
            self.combo_dem_layer.setVisible(True)
            self.combo_dem_layer.setEnabled(is_dem)
            self.btn_load_dem.setVisible(True)
            self.btn_load_dem.setEnabled(is_dem)

            self.lbl_contour.setVisible(True)
            self.combo_contour_layer.setVisible(True)
            self.combo_contour_layer.setEnabled(is_contour)
            self.btn_load_contour.setVisible(True)
            self.btn_load_contour.setEnabled(is_contour)

            self.combo_slope_layer.setEnabled(is_slope)
            self.btn_load_slope.setEnabled(is_slope)
            self.combo_contour_field.setEnabled(is_contour)
        else:
            # In Basic Mode, show ONLY the relevant single terrain combo cleanly
            self.lbl_contour.setVisible(False)
            self.btn_load_dem.setVisible(False)
            self.btn_load_contour.setVisible(False)
            self.lbl_dem.setVisible(mode != "preset")
            self.lbl_dem.setText(tr_text("lbl_terrain_layer", lang))
            self.combo_dem_layer.setVisible(is_dem)
            self.combo_dem_layer.setEnabled(is_dem)
            self.combo_contour_layer.setVisible(is_contour)
            self.combo_contour_layer.setEnabled(is_contour)

    def _update_contour_fields(self):
        self.combo_contour_field.blockSignals(True)
        self.combo_contour_field.clear()
        layer_id = self.combo_contour_layer.currentData()
        if layer_id:
            layer = QgsProject.instance().mapLayer(layer_id)
            if layer and isinstance(layer, QgsVectorLayer) and layer.isValid():
                for fn in [f.name() for f in layer.fields()]:
                    self.combo_contour_field.addItem(fn, fn)
                best_field = detect_elevation_field(layer)
                if best_field:
                    idx = self.combo_contour_field.findText(best_field)
                    if idx >= 0:
                        self.combo_contour_field.setCurrentIndex(idx)
        self.combo_contour_field.blockSignals(False)

    def _update_bldg_fields(self):
        self.combo_bldg_field.blockSignals(True)
        self.combo_bldg_field.clear()
        layer_id = self.combo_bldg_layer.currentData()
        if layer_id:
            layer = QgsProject.instance().mapLayer(layer_id)
            if layer and isinstance(layer, QgsVectorLayer) and layer.isValid():
                for fn in [f.name() for f in layer.fields()]:
                    self.combo_bldg_field.addItem(fn, fn)
                best_field = detect_building_floors_field(layer)
                if best_field:
                    idx = self.combo_bldg_field.findText(best_field)
                    if idx >= 0:
                        self.combo_bldg_field.setCurrentIndex(idx)
        self.combo_bldg_field.blockSignals(False)

    def _on_load_dem_file(self):
        lang = get_language()
        start_dir = QgsProject.instance().homePath() or os.path.expanduser("~")
        fn, _ = QFileDialog.getOpenFileName(
            self,
            tr_text("file_dlg_dem", lang),
            start_dir,
            "GeoTIFF Raster (*.tif *.tiff *.dem *.img);;All Files (*)",
        )
        if fn:
            layer = QgsRasterLayer(fn, os.path.splitext(os.path.basename(fn))[0])
            if layer.isValid():
                QgsProject.instance().addMapLayer(layer)
                self._refresh_topography_layers()
                idx = self.combo_dem_layer.findData(layer.id())
                if idx >= 0:
                    self.combo_dem_layer.setCurrentIndex(idx)
            else:
                QMessageBox.warning(self, tr_text("msg_error", lang), f"Could not load raster: {fn}")

    def _on_load_slope_file(self):
        lang = get_language()
        start_dir = QgsProject.instance().homePath() or os.path.expanduser("~")
        fn, _ = QFileDialog.getOpenFileName(
            self,
            tr_text("file_dlg_slope", lang),
            start_dir,
            "GeoTIFF Raster (*.tif *.tiff *.dem *.img);;All Files (*)",
        )
        if fn:
            layer = QgsRasterLayer(fn, os.path.splitext(os.path.basename(fn))[0])
            if layer.isValid():
                QgsProject.instance().addMapLayer(layer)
                self._refresh_topography_layers()
                idx = self.combo_slope_layer.findData(layer.id())
                if idx >= 0:
                    self.combo_slope_layer.setCurrentIndex(idx)
            else:
                QMessageBox.warning(self, tr_text("msg_error", lang), f"Could not load raster: {fn}")

    def _on_load_contour_file(self):
        lang = get_language()
        start_dir = QgsProject.instance().homePath() or os.path.expanduser("~")
        fn, _ = QFileDialog.getOpenFileName(
            self,
            tr_text("file_dlg_contour", lang),
            start_dir,
            "Vector Layers (*.gpkg *.shp *.dxf *.geojson);;All Files (*)",
        )
        if fn:
            layer = QgsVectorLayer(fn, os.path.splitext(os.path.basename(fn))[0], "ogr")
            if layer.isValid():
                QgsProject.instance().addMapLayer(layer)
                self._refresh_topography_layers()
                idx = self.combo_contour_layer.findData(layer.id())
                if idx >= 0:
                    self.combo_contour_layer.setCurrentIndex(idx)
            else:
                QMessageBox.warning(self, tr_text("msg_error", lang), f"Could not load vector: {fn}")

    def _on_vertical_exaggeration_changed(self, idx):
        if self._updating_ui:
            return
        factor = float(self.combo_exag.itemData(idx) or 1.0)
        self.current_profile.vertical_exaggeration = factor
        self.profile_canvas.update()
        self._update_profile_analysis_banner()

    def _update_profile_analysis_banner(self):
        lang = get_language()
        stats = self.current_profile.get_statistics()
        if not stats:
            self.lbl_profile_analysis.setText(tr_text("prof_status_waiting", lang))
            return

        tot_l = stats.get("total_length", 0.0)
        min_z = stats.get("min_elevation", 0.0)
        max_z = stats.get("max_elevation", 0.0)
        dz = stats.get("elevation_delta", 0.0)
        max_s = stats.get("max_slope_pct", 0.0)
        avg_s = stats.get("avg_slope_pct", 0.0)
        crit_s = stats.get("has_critical_slope", False)
        crit_l = stats.get("critical_slope_length", 0.0)
        b_cnt = stats.get("building_count", 0)
        cut_cnt = stats.get("cut_building_count", b_cnt)
        sil_cnt = stats.get("silhouette_building_count", 0)
        look_dir = stats.get("look_direction", "auto")
        v_ex = self.current_profile.vertical_exaggeration

        look_tr = tr_text(f"look_name_{look_dir}", lang)
        if sil_cnt > 0 or cut_cnt != b_cnt:
            b_summary = tr_text("b_count_cut_sil", lang, total=b_cnt, cut=cut_cnt, sil=sil_cnt)
        else:
            b_summary = tr_text("b_count_simple", lang, total=b_cnt)

        if crit_s:
            self.lbl_profile_analysis.setStyleSheet(
                "font-size: 11px; font-weight: bold; border-radius: 6px; padding: 2px 10px; "
                "background-color: #fef2f2; border: 1.5px solid #f87171; color: #991b1b;"
            )
            self.lbl_profile_analysis.setText(
                tr_text(
                    "prof_status_crit",
                    lang,
                    max_s=max_s,
                    avg_s=avg_s,
                    min_z=min_z,
                    max_z=max_z,
                    dz=dz,
                    tot=tot_l,
                    crit_l=crit_l,
                    b_sum=b_summary,
                    look=look_tr,
                    ex=v_ex,
                )
            )
        else:
            self.lbl_profile_analysis.setStyleSheet(
                "font-size: 11px; font-weight: bold; border-radius: 6px; padding: 2px 10px; "
                "background-color: #f0fdf4; border: 1.5px solid #86efac; color: #166534;"
            )
            self.lbl_profile_analysis.setText(
                tr_text(
                    "prof_status_ok",
                    lang,
                    max_s=max_s,
                    avg_s=avg_s,
                    min_z=min_z,
                    max_z=max_z,
                    dz=dz,
                    tot=tot_l,
                    b_sum=b_summary,
                    look=look_tr,
                    ex=v_ex,
                )
            )

    def _sample_active_topography(self, pt_a: QgsPointXY, pt_b: QgsPointXY) -> UrbanProfile:
        lang = get_language()
        mode = self.combo_topo_mode.currentData() or "dem"
        step_m = self.spin_step_m.value()
        v_ex = float(self.combo_exag.currentData() or 1.0)
        title = self.txt_profile_title.text() or tr_text("default_profile_title", lang)

        proj = QgsProject.instance()

        dem_layer = proj.mapLayer(self.combo_dem_layer.currentData()) if self.combo_dem_layer.currentData() else None
        slope_layer = proj.mapLayer(self.combo_slope_layer.currentData()) if self.combo_slope_layer.currentData() else None
        contour_layer = proj.mapLayer(self.combo_contour_layer.currentData()) if self.combo_contour_layer.currentData() else None
        contour_field = self.combo_contour_field.currentData() or "kot"
        bldg_layer = proj.mapLayer(self.combo_bldg_layer.currentData()) if self.combo_bldg_layer.currentData() else None
        bldg_field = self.combo_bldg_field.currentData()
        road_layer = proj.mapLayer(self.combo_road_layer.currentData()) if self.combo_road_layer.currentData() else None

        look_mode = self.combo_look_mode.currentData() or "auto"
        look_depth = self.spin_look_depth.value()
        include_trees = self.chk_profile_trees.isChecked()

        return sample_profile_between_points(
            pt_a=pt_a,
            pt_b=pt_b,
            title=title,
            source_mode=mode,
            step_meters=step_m,
            vertical_exaggeration=v_ex,
            dem_layer=dem_layer,
            slope_layer=slope_layer,
            contour_layer=contour_layer,
            contour_elev_field=contour_field,
            building_layer=bldg_layer,
            building_floors_field=bldg_field,
            road_layer=road_layer,
            look_mode=look_mode,
            look_depth=look_depth,
            auto_detect_layers=False,
            include_placeholder_trees=include_trees,
            language=lang,
        )

    def _on_refresh_profile_from_layers(self):
        lang = get_language()
        pt_a = self.last_pt_a
        pt_b = self.last_pt_b

        if pt_a is None or pt_b is None:
            ref_layer = None
            dem_id = self.combo_dem_layer.currentData()
            if dem_id:
                ref_layer = QgsProject.instance().mapLayer(dem_id)
            if not ref_layer:
                cnt_id = self.combo_contour_layer.currentData()
                if cnt_id:
                    ref_layer = QgsProject.instance().mapLayer(cnt_id)

            if ref_layer and ref_layer.isValid():
                ext = ref_layer.extent()
                cx = (ext.xMinimum() + ext.xMaximum()) / 2.0
                cy = (ext.yMinimum() + ext.yMaximum()) / 2.0
                pt_a = QgsPointXY(cx - 350.0, cy)
                pt_b = QgsPointXY(cx + 350.0, cy)
                self.last_pt_a = pt_a
                self.last_pt_b = pt_b
            else:
                pt_a = QgsPointXY(0.0, 0.0)
                pt_b = QgsPointXY(700.0, 0.0)

        sampled = self._sample_active_topography(pt_a, pt_b)
        self.master_profile = sampled
        self.current_profile = sampled
        self._sync_ui_from_profile()
        stats = sampled.get_statistics()
        cut_cnt = stats.get("cut_building_count", len(sampled.buildings))
        sil_cnt = stats.get("silhouette_building_count", 0)
        QMessageBox.information(
            self,
            tr_text("msg_prof_updated_title", lang),
            tr_text(
                "msg_prof_updated",
                lang,
                src=sampled.source_layer_name,
                len=sampled.total_length,
                min_z=sampled.min_elevation,
                max_z=sampled.max_elevation,
                tot=len(sampled.buildings),
                cut=cut_cnt,
                sil=sil_cnt,
            ),
        )

    def _on_profile_preset_changed(self, idx):
        if self._updating_ui:
            return
        pid = self.combo_profile_presets.itemData(idx)
        lang = get_language()
        if pid == "preset_aa":
            self.current_profile = preset_profile_hillside_aa(lang=lang)
        else:
            self.current_profile = preset_profile_slope_bb(lang=lang)
        self._sync_ui_from_profile()

    def _on_profile_title_changed(self, text):
        self.current_profile.title = text
        self.profile_canvas.update()

    def _on_sky_theme_changed(self, idx):
        if self._updating_ui:
            return
        theme = self.combo_sky.itemData(idx) or "sunset"
        self.current_profile.sky_theme = theme
        self.profile_canvas.update()

    def _on_profile_building_clicked(self, idx):
        lang = get_language()
        if 0 <= idx < len(self.current_profile.buildings):
            b = self.current_profile.buildings[idx]
            self.lbl_prof_bldg.setText(tr_text("mass_info_sel", lang, idx=idx + 1, floors=b.floors, width=b.width))
            self.spin_prof_floors.blockSignals(True)
            self.spin_prof_floors.setValue(b.floors)
            self.spin_prof_floors.blockSignals(False)

            self.spin_prof_width.blockSignals(True)
            self.spin_prof_width.setValue(b.width)
            self.spin_prof_width.blockSignals(False)

    def _on_prof_floors_changed(self, val):
        idx = self.profile_canvas.selected_bldg_idx
        if 0 <= idx < len(self.current_profile.buildings):
            b = self.current_profile.buildings[idx]
            b.floors = int(val)
            b.height = b.floors * b.floor_height
            b.top_elevation = b.ground_elevation + b.height
            self.profile_canvas.update()

    def _on_prof_width_changed(self, val):
        idx = self.profile_canvas.selected_bldg_idx
        if 0 <= idx < len(self.current_profile.buildings):
            b = self.current_profile.buildings[idx]
            b.width = float(val)
            b.end_dist = b.start_dist + b.width
            self.profile_canvas.update()

    def _on_add_building_to_profile(self):
        lang = get_language()
        mid = self.current_profile.total_length * 0.5
        elev = self.current_profile.get_elevation_at(mid)
        new_b = BuildingMass(
            start_dist=mid - 12.0,
            end_dist=mid + 12.0,
            ground_elevation=elev,
            floors=4,
            label=tr_text("new_bldg_label", lang),
        )
        self.current_profile.add_building(new_b)
        self.profile_canvas.update()
        self._update_profile_analysis_banner()

    def _on_del_building_from_profile(self):
        lang = get_language()
        idx = self.profile_canvas.selected_bldg_idx
        if 0 <= idx < len(self.current_profile.buildings):
            self.current_profile.buildings.pop(idx)
            self.profile_canvas.selected_bldg_idx = -1
            self.lbl_prof_bldg.setText(tr_text("mass_info_none", lang))
            self.profile_canvas.update()
            self._update_profile_analysis_banner()

    def _on_add_tree_cluster(self):
        mid = self.current_profile.total_length * 0.35
        elev = self.current_profile.get_elevation_at(mid)
        self.current_profile.add_vegetation(
            VegetationCluster(center_dist=mid, ground_elevation=elev, width=18.0, tree_count=4)
        )
        self.profile_canvas.update()

    def toggle_collapse(self, collapse: Optional[bool] = None):
        lang = get_language()
        if collapse is None:
            collapse = not self.is_collapsed
        self.is_collapsed = collapse

        if self.is_collapsed:
            self.main_tabs.setVisible(False)
            self.mini_bar_widget.setVisible(True)
            self.btn_minimize_drawer.setText(tr_text("btn_expand", lang))
            self.btn_minimize_drawer.setStyleSheet(
                "QPushButton { font-weight: bold; font-size: 11px; padding: 4px 12px; "
                "background-color: #38bdf8; color: #0f172a; border: 1.5px solid #0284c7; border-radius: 6px; }"
            )
            self.setMinimumSize(420, 60)
            self.resize(740, 75)
        else:
            self.mini_bar_widget.setVisible(False)
            self.main_tabs.setVisible(True)
            self.btn_minimize_drawer.setText(tr_text("btn_collapse", lang))
            self.btn_minimize_drawer.setStyleSheet(
                "QPushButton { font-weight: bold; font-size: 11px; padding: 4px 12px; "
                "background-color: #f8fafc; color: #0f172a; border: 1.5px solid #94a3b8; border-radius: 6px; }"
            )
            self.setMinimumSize(960, 680)
            self.resize(1240, 800)

    def _on_toggle_drawer_clicked(self):
        self.toggle_collapse()

    def _on_mini_bar_cancel(self):
        if self.map_tool_section and self.iface:
            self.iface.mapCanvas().unsetMapTool(self.map_tool_section)
        self.toggle_collapse(False)

    def _on_map_point_a_picked(self, pt_a):
        self.lbl_mini_status.setText(tr_text("mini_pick_b", get_language(), x=pt_a.x(), y=pt_a.y()))

    def _on_start_map_section_tool(self):
        lang = get_language()
        if not self.iface:
            QMessageBox.information(self, tr_text("msg_info", lang), tr_text("msg_need_gui", lang))
            return

        canvas = self.iface.mapCanvas()
        look_mode = self.combo_look_mode.currentData() or "auto"
        look_depth = self.spin_look_depth.value()
        self.map_tool_section = SectionLineMapTool(
            canvas,
            look_mode=look_mode,
            look_depth=look_depth,
        )
        self.map_tool_section.sectionLineCompleted.connect(self._on_map_section_completed)
        self.map_tool_section.firstPointPicked.connect(self._on_map_point_a_picked)
        canvas.setMapTool(self.map_tool_section)

        self.toggle_collapse(True)
        self.lbl_mini_status.setText(tr_text("mini_pick_a", lang))
        if self.iface.messageBar():
            self.iface.messageBar().pushInfo("urban_cross_section", tr_text("msg_pick_bar", lang))

    def _on_map_section_completed(self, pt_a: QgsPointXY, pt_b: QgsPointXY):
        lang = get_language()
        self.lbl_mini_status.setText(tr_text("mini_calculating", lang))
        self.last_pt_a = pt_a
        self.last_pt_b = pt_b
        sampled_prof = self._sample_active_topography(pt_a, pt_b)
        self.master_profile = sampled_prof
        self.current_profile = sampled_prof

        self.toggle_collapse(False)
        self.showNormal()
        self.raise_()
        self.activateWindow()

        self._sync_ui_from_profile()
        stats = sampled_prof.get_statistics()
        cut_cnt = stats.get("cut_building_count", len(sampled_prof.buildings))
        sil_cnt = stats.get("silhouette_building_count", 0)
        QMessageBox.information(
            self,
            tr_text("msg_prof_created_title", lang),
            tr_text(
                "msg_prof_created",
                lang,
                len=sampled_prof.total_length,
                src=sampled_prof.source_layer_name,
                tot=len(sampled_prof.buildings),
                cut=cut_cnt,
                sil=sil_cnt,
                look=sampled_prof.look_direction,
                depth=sampled_prof.look_depth,
            ),
        )

    def _on_add_profile_to_print_layout(self):
        lang = get_language()
        tmp_dir = os.path.join(QgsProject.instance().homePath() or os.path.expanduser("~"), "output")
        os.makedirs(tmp_dir, exist_ok=True)
        tmp_svg = os.path.join(tmp_dir, "urban_profile_1000_layout.svg")

        SvgUrbanProfileExporter(self.current_profile).save_to_file(tmp_svg)
        layout_name = "1-1000 Kentsel Kesitler Paftası" if lang == "tr" else "1-1000 Urban Sections Layout"
        try:
            insert_section_image_to_layout(
                image_path=tmp_svg,
                layout_name=layout_name,
                x_mm=20.0,
                y_mm=30.0,
                width_mm=260.0,
                height_mm=80.0,
            )
            QMessageBox.information(self, tr_text("msg_info", lang), tr_text("msg_layout_added", lang, path=tmp_svg))
        except Exception as e:
            QMessageBox.critical(self, tr_text("msg_error", lang), str(e))

    def _on_export_profile_svg(self):
        lang = get_language()
        fn, _ = QFileDialog.getSaveFileName(
            self,
            tr_text("file_dlg_svg", lang),
            f"{self.current_profile.title.replace(' ', '_')}.svg",
            "SVG (*.svg)",
        )
        if fn:
            SvgUrbanProfileExporter(self.current_profile).save_to_file(fn)
            QMessageBox.information(self, tr_text("msg_info", lang), tr_text("msg_saved", lang, path=fn))

    def _on_export_profile_png(self):
        lang = get_language()
        fn, _ = QFileDialog.getSaveFileName(
            self,
            tr_text("file_dlg_png", lang),
            f"{self.current_profile.title.replace(' ', '_')}.png",
            "PNG (*.png)",
        )
        if fn:
            self.profile_canvas.export_to_image(fn, dpi=300)
            QMessageBox.information(self, tr_text("msg_info", lang), tr_text("msg_saved", lang, path=fn))
