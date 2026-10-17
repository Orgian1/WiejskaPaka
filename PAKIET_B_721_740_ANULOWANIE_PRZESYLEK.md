# B/721–B/740 — anulowanie całej przesyłki

- Nowy endpoint POST /shipments/{shipment_id}/cancel-test dla właściciela przesyłki.
- Anulowanie jest atomowe i możliwe tylko gdy wszystkie zamówienia oczekują na testową płatność.
- Stany magazynowe wszystkich produktów są przywracane jeden raz.
- Zablokowano anulowanie pojedynczego zamówienia należącego do przesyłki, aby nie rozdzielać opłaty dostawy.
- Ponowne anulowanie zwraca HTTP 409; cudza przesyłka HTTP 404.
- Płatności i zwroty pozostają wyłącznie testowe.
- Testy uruchamiano osobno ze względu na izolację baz danych w dotychczasowym zestawie testowym.
- Brak testu z PostgreSQL/Neon i pełnej regresji.
