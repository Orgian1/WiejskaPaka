# WiejskaPaka — PostgreSQL, pakiet 02

## Zmiany
- Zaostrzono ochronę przed przypadkowym uruchomieniem testów DDL na niewłaściwej bazie.
- Odrzucane są parametry DSN mogące przekierować połączenie (`dbname`, `host`, `service`, `options`), wielohostowe adresy, niejednoznaczne ścieżki i powtarzające się `sslmode`.
- Dopuszczone są tylko jawnie określone parametry nieroutujące (`sslmode`, `connect_timeout`, `application_name`).
- Dodano 12 testów regresyjnych.

## Weryfikacja
- 21/21 testów ochrony konfiguracji PostgreSQL zaliczonych.
- Pełny zestaw na nowej bazie SQLite: 2392 zaliczone, 4 pominięte, 16 podtestów zaliczonych.
- Pierwsze uruchomienie na domyślnej, zastanej bazie SQLite miało 19 błędów (m.in. konflikty rejestracji 409); po izolacji bazy wszystkie testy przeszły. Testy wymagają świeżej bazy.
- **Nie uruchamiano rzeczywistego PostgreSQL ani Neon.**

## Ograniczenia
To jest ochrona przed przypadkową pomyłką konfiguracyjną, nie granica bezpieczeństwa. Nie zastępuje odrębnego użytkownika DB, ograniczeń DDL, kopii zapasowych ani odizolowanego środowiska testowego. RLS nie zostało włączone. Płatności produkcyjne pozostają wyłączone. Publiczna strona wiejskapaka.pl nie została zmieniona.
