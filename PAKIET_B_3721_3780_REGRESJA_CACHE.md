# WiejskaPaka B/3721–B/3780 — kontrola regresji

- Uruchomiono 13 modułów testowych związanych z ostatnimi zmianami; wszystkie zakończyły się wynikiem PASS. Szczegóły: `REGRESJA_B_3721_BATCH.json`.
- Ulepszono `scripts/run_tests_per_file.py`: raport zawiera odcisk kodu aplikacji (backend/web/database/scripts). Przy wznowieniu nie wolno ponownie używać zaliczonych testów, jeżeli kod aplikacji uległ zmianie; `--refresh-stale` uruchamia je od nowa.
- Dodano testy integralności odcisku kodu.
- Nie ukończono jeszcze pełnej regresji 2805 testów, testów PostgreSQL ani mobilnych.
- Nie zmieniano konfiguracji Neon i nie podłączano rzeczywistych płatności.
