# WiejskaPaka B/11301 — PostgreSQL DSN allowlist

- Zastąpiono czarną listę parametrów URL PostgreSQL listą dozwolonych opcji (`sslmode`, `connect_timeout`, `application_name`).
- Nieznane opcje libpq są odrzucane, aby uniknąć niekontrolowanego routingu lub zmiany zachowania połączenia.
- `connect_timeout` ograniczony do 1–30 sekund, `application_name` do bezpiecznego identyfikatora ASCII.
- Dodano 25 przypadków testowych i sprawdzono regresję od B/11289 do B/11301.
- Wynik: 143 PASS, 0 FAIL.
- Testy lokalne, bez prawdziwego serwera PostgreSQL. Brak gotowości produkcyjnej i aktywnych płatności.
