# B/901–B/960 — odczytowy audyt spójności przesyłek

Nowe API: `GET /admin/shipments/reconciliation?only_issues=true&limit=100&offset=0`.
Dostęp tylko dla administratora. Nie zmienia płatności ani bazy danych.

Wykrywa: brak pozycji przesyłki, rozbieżność kosztu dostawy, koszt dostawy przy odbiorze osobistym, błędną sumę pozycji, mieszane statusy, zwroty przekraczające kwoty zamówień. Wszystkie wartości w groszach.

Ograniczenia: raport analizuje przesyłki w pamięci przed stronicowaniem; dla bardzo dużej bazy wymaga optymalizacji. Nie zastępuje audytu księgowego ani integracji płatności. Testy SQLite, nie testowano Neon.
