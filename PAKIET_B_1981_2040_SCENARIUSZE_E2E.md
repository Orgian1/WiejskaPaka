# WiejskaPaka — pakiet B/1981–B/2040: regresja procesu przesyłki

Dodano `tests/test_b1981_end_to_end_shipment.py` — trzy scenariusze integracyjne na lokalnej bazie SQLite:

1. Dwa produkty w przesyłce odbieranej osobiście, gotowość, kontrola uprawnień, wymagane sprawdzenie towaru, jeden PIN, brak możliwości ponownego potwierdzenia i anulowania po odbiorze.
2. Dwa produkty z jedną opłatą dostawy 450 groszy, symulacja opłacenia każdej pozycji, atomowy zwrot 4450 groszy, ochrona przed podwójnym zwrotem i podwójnym przywróceniem magazynu.
3. Anulowanie nieopłaconej przesyłki, uprawnienia właściciela, przywrócenie zapasu dokładnie raz i odmowa ponownego anulowania.

Testy wykonane lokalnie: `python -m pytest -q tests/test_b1981_end_to_end_shipment.py` — 3 zaliczone.
`python -m compileall -q backend` — zaliczone.

Ograniczenia: testy SQLite, bez rzeczywistej bramki płatniczej, bez PostgreSQL, bez testów przeglądarkowych i bez pełnej regresji. Testy w tym pliku uruchamiane są w ustalonej kolejności, korzystając z jednej izolowanej bazy testowej.
