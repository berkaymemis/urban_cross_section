# 🗺️ `gis/` — UrbanCrossSection PyQGIS Entegrasyon Katmanı

Bu dizin, QGIS harita tuvali, vektör katmanları ve Baskı Düzeni (Print Layout) ile etkileşimi yönetir.

## Modüller
* `compat.py` — Qt5 (QGIS 3) ve Qt6 (QGIS 4) çift çalışma zamanı uyumluluk köprüsü (`QAction`, enumlar, painter render hints).
* `layer_reader.py` — Projedeki yol çizgilerini tespit etme, genişlik alanlarını (`genislik`, `width`) otomatik okuma ve seçili yol bilgilerini ayıklama.
* `cross_line_gen.py` — Yola dik (enine) teğet açısını hesaplayıp haritada `A - A'` kesit çizgisi oluşturma.
* `layout_inserter.py` — Çizilen kesiti aktif QGIS Print Layout'a (Jüri Paftası) resim öğesi olarak ekleme.
