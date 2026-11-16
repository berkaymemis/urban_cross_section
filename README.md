# urban_cross_section

**urban_cross_section** is a dual-mode QGIS plugin (compatible with **QGIS 3.28+ / Qt5** and **QGIS 4.x / Qt6**) for urban planners, landscape architects, and transportation engineers. It combines a Streetmix-style street cross-section editor (`1:100`) with a live `1:1000` topographic & building skyline section extractor directly from QGIS map layers.

---

## Features

1. **Dual-Mode Interface (`Basic` & `Advanced`):**
   - **Basic Mode (Default):** Clean, streamlined controls for picking templates or drawing map section lines and exporting immediately.
   - **Advanced Mode:** Reveals underground utility networks (`Water`, `Fiber`, `Power`, `Gas`, `Stormwater`, `Sewer`, `Concrete Box Gallery`), layer visibility toggles, side building parameters, geotechnical subgrades, vertical exaggeration (`1x–10x`), corridor depth, road intersection labels, and manual mass editing.
2. **100% English Default + Live `EN | TR` Switch:** Opens cleanly in English and supports instant toggling between English and Turkish without altering any geometric measurements or layer data.
3. **1:100 Street Cross-Section Designer:**
   - Built-in multi-modal presets from `7 m` calmed residential streets to `50 m` expressways.
   - Interactive canvas with click-to-select lanes, `[ - ] / [ + ]` width steppers, and clickable underground utility pipes.
   - Reads road widths and names directly from selected QGIS line features and generates perpendicular `A - A'` section lines on the map.
4. **1:1000 Urban Profile & Topographic Skyline Extractor (`A - B`):**
   - Samples **DEM rasters**, **DEM + Slope rasters**, or **Vector Contour lines** (using monotonic PCHIP interpolation).
   - Projects directly cut building polygons (`Section Cut`) as well as street-fronting buildings within the selectable **Look Direction** corridor (`Auto`, `Left`, `Right`, `Both Sides`, or `Cut Only`), parsing multi-format floor fields (`4`, `"Z+3"`, `"4 Kat"`, etc.).
   - Automatic multi-sheet segmentation into `700 m` jury/CAD sheets for long corridors.
5. **Zero External Dependencies:** Pure Python architectural vector SVG export, 300 DPI PNG export, native QGIS Print Layout insertion, and Processing Toolbox algorithms (`Generate Perpendicular Section Lines`, `Batch Export Vector Sections`).

---

## Architecture

* `core/` — Pure Python domain models, i18n dictionary (`EN` / `TR`), presets, PCHIP interpolation, and SVG exporters (zero `qgis` / `PyQt` imports).
* `gis/` — PyQGIS adapters, Qt5/Qt6 compatibility layer (`compat.py`), map A-B picker (`map_tool_section.py`), DEM/Contour/Corridor sampler (`profile_sampler.py`), and Print Layout inserter.
* `ui/` — `QPainter` live canvases (`canvas_widget.py`, `profile_canvas.py`) and dual-mode dialog (`main_dialog.py`).
* `processing_provider/` — Native QGIS Processing Toolbox provider & batch export algorithms.
* `tests/` — Unit tests (`test_core_sections.py`) and dual-runtime headless PyQGIS smoke tests (`qgis_smoke.py`).

---

*Author: Berkay Memis | License: GPL-2.0-or-later*
