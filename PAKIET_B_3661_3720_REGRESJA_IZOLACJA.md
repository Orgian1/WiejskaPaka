# WiejskaPaka — B/3661–B/3720: izolacja regresji

## Ustalenia
- Pełny przebieg `pytest -q --maxfail=8` ujawnił 8 błędów po 182 zaliczonych testach. Większość błędów dotyczyła współdzielonego stanu SQLite między modułami (np. `marker already exists`, licznik zamówień) — nie jest to dowód na 8 błędów biznesowych.
- Naprawiono nieaktualny test kontraktu interfejsu `test_b3181_pending_checkout_cart_guard.py` po dodaniu czyszczenia znacznika zakupowego.
- Zmieniono `test_b3481_direct_idempotency.py`, by liczył zamówienia i klucze idempotencji wyłącznie dwóch klientów przygotowanych przez test, a nie wszystkie dane z wcześniejszych testów.
- Testy celowane na odizolowanej bazie: **5 passed**.
- Rozpoczęto regresję plik po pliku z osobnymi bazami; stan cząstkowy zapisano w `REGRESJA_B_3661_BATCH1.json`. Niektóre moduły uruchamiają podprocesy i przekraczają limity; przebieg nie został zakończony.

## Ograniczenia
Nie wykonano pełnej regresji 2805 testów do końca. Nie wykonano testów produkcyjnego PostgreSQL, fizycznego telefonu ani realnych płatności. Nie zmieniano Neon.
