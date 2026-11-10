# WiejskaPaka B/2941–B/3000 — regresja logowania

## Zmiana
Naprawiono symulację DOM w `tests/test_web_login_race.py`: atrapę elementu rozszerzono o `addEventListener` i `querySelector`, których używa bieżący interfejs koszyka. Timer w symulacji uruchamia odroczone asercje bez przetrzymywania procesu przez czas komunikatu UI. Nie osłabiono asercji bezpieczeństwa: spóźniona odpowiedź logowania nie może przywrócić sesji po wylogowaniu.

## Wykonane kontrole
- `pytest -q tests/test_web_login_race.py`: 2 zaliczone.
- Siedem modułów testów przeglądarkowych/sesji: 17 zaliczonych.
- Pięć modułów bezpieczeństwa i sesji: 19 zaliczonych.
- `node --check web/app.js`: poprawnie.
- `python -m compileall -q backend`: poprawnie.

## Ograniczenia
Nie wykonano ponownie pełnych 200 modułów regresji. Testy Node wykorzystują atrapę DOM, nie prawdziwą przeglądarkę. Nie testowano PostgreSQL ani produkcyjnych płatności. Neon, hosting i domena bez zmian.
