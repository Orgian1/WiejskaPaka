# WiejskaPaka B/2101–B/2160 — rozszerzona brama regresji

Dodano `scripts/run_extended_release_gate.py`: 24 obowiązkowe moduły testowe z czterech obszarów (zakupy/magazyn, dostawa/odbiór, anulowania/finanse, interfejs/administracja). Każdy moduł działa w odrębnym procesie i na lokalnej bazie SQLite, bez dostępu do produkcyjnych usług. Brama kończy się błędem, jeżeli brakuje któregokolwiek modułu lub jeśli moduły są powtórzone.

Dodano `tests/test_b2101_extended_gate_manifest.py` (2 testy). Zweryfikowano wszystkie 24 moduły w dwóch kolejnych partiach: 24/24 PASS. Raport: `extended_release_gate_verified_report.json`. Pierwszy pełny przebieg został przerwany przez limit czasu wykonania narzędzia po 11 modułach; pozostałe 13 uruchomiono osobno. Nie jest to potwierdzenie jednego nieprzerwanego przebiegu bramy.

Uruchomienie lokalne: `python scripts/run_extended_release_gate.py`. Pełna regresja wszystkich modułów, testy w przeglądarce oraz testy PostgreSQL wciąż są do wykonania. Nie zmieniono konfiguracji Neon, domeny, hostingu ani płatności produkcyjnych.
