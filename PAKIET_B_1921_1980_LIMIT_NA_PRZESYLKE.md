# WiejskaPaka B/1921–B/1980 — spójność limitów i wyceny wielu rolników

- Koszyk zapisany: limit 50 różnych produktów na rolnika/przesyłkę, nie na cały koszyk. Aktualizacja istniejącej pozycji nie zużywa nowego miejsca.
- API POST /cart/quote: do 500 pozycji w zapytaniu, ale maksymalnie 50 dla każdego rolnika; zgodność z ograniczeniem checkout.
- API wyceny: dodatkowe pole `shipments` z farmer_id, items_count, subtotal_grosze, delivery_grosze i total_grosze; wcześniejsze pola pozostają dostępne.
- Wycena tylko informacyjna, bez rezerwacji magazynu i bez płatności.
- Testy: 100 pozycji u dwóch rolników, 51. pozycja odrzucona, aktualizacja dozwolona, sumowanie groszy i odbiór bez opłaty.
- Testy lokalne SQLite: 3 passed (nowe i istniejący test wyceny); compileall backend OK.
- Nie wykonano pełnej regresji, testów przeglądarkowych ani testów PostgreSQL.
- Nie zmieniano konfiguracji Neon, hostingu, domeny ani integracji płatności.
