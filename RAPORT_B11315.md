# WiejskaPaka B/11315 — generator planu migracji

- Dodano `database/generate_test_migration_plan.py`, który tworzy skrypt shell **bez wykonywania SQL**.
- Wygenerowany plan najpierw sprawdza manifest i blokadę SHA-256 wszystkich migracji, potem weryfikuje pustą bazę i uprawnienia konta, dopiero następnie zawiera 23 polecenia `psql` i końcową weryfikację schematu.
- `set -eu` zatrzymuje plan po błędzie polecenia lub brakującej zmiennej.
- Generator nie nadpisuje istniejących plików; tworzy plik z uprawnieniami 0600.
- 187 testów wybranego zestawu: PASS; 0 błędów.
- **Nie wykonano migracji na żywym PostgreSQL**. Plan pozostaje sekwencyjny, nieatomowy; po błędzie trzeba usunąć i odtworzyć dedykowaną pustą bazę testową.
- Uruchomienie: `python -m database.generate_test_migration_plan --output plan_test_postgres.sh`; przed wykonaniem ręcznie przejrzeć wygenerowany skrypt i ustawić poprawne środowisko testowe.
