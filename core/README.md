# `core/` — UrbanCrossSection Pure Python Business Logic

This directory contains all mathematical, geometric, i18n, and vector SVG export logic for `UrbanCrossSection` with zero `qgis.*` or `PyQt*` dependencies.

## Modules
* `i18n.py` — Pure Python EN (default) / TR bilingual translation dictionary and non-destructive retranslation helpers.
* `elements.py` — Sidewalk, travel lane, bike lane, median, parklet, and building facade models.
* `section_model.py` — Street cross-section builder, width balance validator, and utility flags.
* `presets.py` — Built-in 7m–50m multi-modal street cross-section templates.
* `svg_exporter.py` — Pure Python street cross-section SVG renderer.
* `profile_model.py` — 1:1000 urban skyline, terrain PCHIP interpolation, slope analysis, and multi-sheet segmenter.
* `profile_svg.py` — Pure Python 1:1000 elevation profile SVG renderer.
