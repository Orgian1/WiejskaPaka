# Weryfikacja 06 — bezpieczeństwo migracji danych

Wykryto istotne ryzyko: istniejący migrator `database/migrate_sqlite_to_postgres.py`
obsługiwał tylko osiem tabel z pierwszego etapu. Nowsze moduły aplikacji
przechowują dane również w kolejnych tabelach. Przeniesienie tylko ośmiu
tabel mogłoby dać fałszywe poczucie udanej migracji i pozostawić część danych
poza PostgreSQL.

Dodano zasadę **fail closed**: jeżeli SQLite zawiera dodatkowe niepuste tabele,
migrator przerywa działanie przed zapisem do PostgreSQL i pokazuje ich nazwy
oraz liczbę rekordów. Dodano trzy testy regresyjne.

**Ograniczenie:** nie opracowano jeszcze pełnej migracji wszystkich tabel.
Nie należy używać starego migratora do przenoszenia istniejących danych
użytkowników. Testy na żywym PostgreSQL nadal wymagają izolowanej bazy.
