# WiejskaPaka — B/11305

Dodano `database/test_schema_manifest.py`: uporządkowany, wyłącznie odczytowy manifest pliku bazowego i 22 skryptów rozszerzających schemat PostgreSQL. Zawiera sumy SHA-256 i wykrywa brakujące/puste skrypty. Statyczny test potwierdza, że wszystkie 14 tabel potrzebnych przy starcie API mają deklaracje CREATE TABLE w zestawie skryptów.

Dodano pięć testów `tests/test_b11305_migration_manifest.py`. Uruchomiono zestaw `test_b1130*.py`, `test_b1129*.py` i `test_b11289_test_server_preflight.py`: **168 passed**.

**Ograniczenia:** brak podłączonej instancji PostgreSQL; nie wykonywano skryptów SQL na serwerze, nie zweryfikowano ich kompatybilności i pełnej kolejności zależności w rzeczywistej bazie. Manifest nie jest automatycznym migratorem i nie uprawnia do uruchomienia produkcji. Przed testowym VPS trzeba uruchomić SQL na pustej bazie testowej i wykonać testy integracyjne.
