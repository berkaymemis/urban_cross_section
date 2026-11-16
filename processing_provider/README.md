# ⚙️ `processing_provider/` — UrbanCrossSection QGIS Processing Katmanı

Bu dizin, QGIS İşlem Araç Kutusu (Processing Toolbox) ve Grafiksel Modelleyici (Graphical Modeler) algoritmalarını içerir.

## Algoritmalar
* `GenerateCrossSectionLinesAlgorithm` (`generate_cross_sections`) — Yol katmanı boyunca teğet açısını hesaplayarak dik enine kesit hatları üretir.
* `BatchExportSectionsAlgorithm` (`batch_export_sections`) — Projede yer alan tüm benzersiz yol genişliklerini tespit edip SVG kesit dosyalarını toplu olarak dışa aktarır.
