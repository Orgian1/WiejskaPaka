# WiejskaPaka B/431–B/460 — graficzny koszyk testowy

Zmiany rzeczywiste: dodano widok koszyka, przyciski dodawania, aktualizacji i usuwania produktów, wybór punktu odbioru/adresu dostawy, uruchamianie testowego checkoutu, wyświetlanie kodów testowych PIN i komunikat o koszyku wielu sprzedawców. Backend: rozpoczęcie transakcji checkoutu uwzględnia PostgreSQL (BEGIN zamiast SQLite BEGIN IMMEDIATE).

Ograniczenia: koszyk wielu rolników nie może być jeszcze finalizowany jednym żądaniem. Dostawa nadal jest naliczana osobno dla każdej pozycji checkoutu. Nie wykonano testów E2E w przeglądarce ani z Neon. Brak prawdziwych płatności. PIN-y testowe nie powinny być używane w środowisku produkcyjnym. Oznaczenie zakresu B/431–B/460 nie oznacza 30 osobnych funkcji.

Weryfikacja: `node --check web/app.js`, `python -m py_compile backend/app.py`, `python -m pytest -q tests/test_b401_checkout.py tests/test_b371_saved_cart.py` (3 passed).
