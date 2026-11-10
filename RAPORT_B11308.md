# WiejskaPaka B/11308 — plan uruchomienia migracji

- Dodano `database/test_schema_runbook.py`: generator offline kolejności 23 skryptów SQL dla **nowej, pustej testowej bazy PostgreSQL**.
- Generator sprawdza SHA-256 względem zatwierdzonej blokady i statyczną obecność 14 tabel wymaganych przy starcie.
- Wynik jest plikiem dla psql z `\\ir` (ścieżki względem pliku); generator **nie łączy się z bazą i nie wykonuje SQL**.
- Skrypty wymagają przeglądu pod kątem transakcyjności, zależności i zgodności z prawdziwym PostgreSQL. Nie uruchamiać na bazie produkcyjnej ani zawierającej dane.
- Uruchomienie generatora: `python -m database.test_schema_runbook --output database/runbook.sql`.
- Testy lokalne: **179 passed** (zestaw B/11289–B/11308), bez rzeczywistej instancji PostgreSQL.

## Budżet i skalowanie
Cel: 30 000 opłaconych zamówień miesięcznie. Najpierw pojedynczy VPS i PostgreSQL, z kopiami zapasowymi, monitoringiem i testami szczytowego obciążenia. Rzeczywiste parametry dopiero po benchmarkach. Płatności produkcyjne wyłączone.
