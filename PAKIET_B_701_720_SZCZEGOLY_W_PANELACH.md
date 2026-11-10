# B/701–B/720 — szczegóły przesyłek w panelach

- Klient, rolnik i dostawca mogą rozwinąć szczegóły swojej przesyłki z API `/shipments/{id}/details`.
- Interfejs pokazuje pozycje, ilości, statusy, kwoty produktów, jednorazowy koszt dostawy i sumę.
- Dla klienta i rolnika pokazuje sumę zarejestrowanych zwrotów **testowych**; dostawca nie widzi danych o zwrotach.
- Szczegóły są pobierane dopiero po kliknięciu, bez zapisu w localStorage.
- Dostęp do danych weryfikuje serwer; UI nie stanowi zabezpieczenia.
- Bez zmian w Neon, integracjach płatności i domenie.

## Weryfikacja
`node --check web/dashboard.js` — OK.
`python -m pytest -q tests/test_b681_shipment_details.py` — 1 passed.

## Ograniczenia
Nie uruchomiono pełnej regresji ani testów w przeglądarce. Status przesyłki nadal wyliczany jest z pozycji zamówienia; należy dalej ujednolicać model stanów i rozliczeń.
