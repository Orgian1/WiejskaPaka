# Pakiet B/311–B/320 — granice kwot zamówień

Zaimplementowano weryfikację zakresu 64-bitowego dla ceny, ilości, dostawy i sumy zamówienia przed zapisem do bazy. W przypadku przekroczenia limitu API zwraca 422 zamiast błędu przepełnienia po stronie sterownika bazy. Obliczenia odbywają się wyłącznie na liczbach całkowitych (groszach).

Nowy moduł: `backend/order_amount_limits.py`. Zmiana w `backend/app.py` w tworzeniu zamówienia. Nowe testy: `tests/test_order_amount_limits.py`.

Zakres nie obejmuje migracji produkcyjnej bazy Neon, rzeczywistych płatności ani pełnej regresji. Numer pakietu to oznaczenie robocze, nie liczba nowych funkcji.
