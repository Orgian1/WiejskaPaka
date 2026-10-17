# Kontynuacja lokalna — 16 października 2026

Wzmocniono `revoke_other_sessions`: funkcja pomocnicza sprawdza istnienie i ważność bieżącej sesji przypisanej do podanego konta przed usunięciem innych tokenów. Dotychczas ochronę zapewniała otaczająca ją transakcja HTTP; teraz także bezpośrednie wywołanie funkcji odmawia działania dla obcego, nieistniejącego lub wygasłego tokenu.

Dodano dwa testy regresyjne, w tym brak zmian w sesjach przy odmowie. Przebieg `python -m pytest -q tests/test_session_revoke_defense.py tests/test_session_security_api.py tests/test_session_security_http.py tests/test_session_security_ui.py`: 49 PASS, 0 FAIL. Pełna regresja i natywny PostgreSQL nie były wykonywane dla tego pakietu; gotowość produkcyjna niepotwierdzona.
