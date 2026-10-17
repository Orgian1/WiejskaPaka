# Pakiet B/1021–B/1080 — kontrole spójności przesyłek

Dodano do istniejącego, tylko-odczytowego endpointu `GET /admin/shipments/reconciliation`:
- wykrywanie niezgodności kupującego, rolnika i rodzaju realizacji między przesyłką a zamówieniami;
- wykrywanie naliczenia dodatniej opłaty za dostawę przy więcej niż jednej pozycji przesyłki;
- wykrywanie ujemnych kwot i nieprawidłowej opłaty przy odbiorze osobistym;
- wykrywanie niepełnego zwrotu testowego po nieudanej dostawie.

Raport nie naprawia danych automatycznie. Zachowano wszystkie istniejące pola API i regułę jednej opłaty za przesyłkę. Nie uruchamiano produkcyjnych płatności ani migracji Neon.

Testy: `python -m pytest -q tests/test_b1021_reconciliation_invariants.py tests/test_b901_reconciliation.py` — 2 passed.

Numeracja to zakres roboczy, nie liczba wdrożonych funkcji. Pozostaje pełna regresja i weryfikacja PostgreSQL.
