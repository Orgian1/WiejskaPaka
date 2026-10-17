# B/961–B/1020 — panel kontroli spójności i audytu

Zaimplementowano w panelu administratora graficzny widok raportu `/admin/shipments/reconciliation` i szczegółowego audytu `/admin/shipments/{id}/audit`.

- Domyślnie wyświetlane są tylko przesyłki z problemami; filtr można wyłączyć.
- Stronicowanie po 30 rekordów, odświeżanie i licznik wyników.
- Każda przesyłka ma przycisk pobierający historię statusów i testowych zwrotów.
- Wyniki prezentowane za pomocą bezpiecznego tworzenia elementów DOM (bez HTML z odpowiedzi serwera).
- Zabezpieczenie przed wyświetleniem spóźnionych odpowiedzi po zmianie sesji, strony lub wybranej przesyłki.
- Moduł tylko do odczytu, nie naprawia automatycznie danych i nie uruchamia zwrotów.

Nie podłączono prawdziwych płatności ani Neon. Nie wykonano testów end-to-end w przeglądarce ani pełnej regresji.
Numeracja pakietu jest zakresem roboczym, nie liczbą niezależnych funkcji.
