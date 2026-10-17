# B/1561–B/1620 — historia finansowa w panelu klienta

- Przycisk „Historia płatności i zwrotów (TEST)” przy każdej przesyłce klienta.
- Pobieranie prywatnego API `/shipments/{id}/financial-history-test` na żądanie.
- Wyświetlanie produktów, pojedynczej opłaty za dostawę przesyłki, sumy, zwrotów testowych, statusów płatności oraz historii zdarzeń zamówień.
- Ostrzeżenie o niespójnej kwocie dostawy.
- Zabezpieczenie przed wyświetleniem spóźnionej odpowiedzi po wylogowaniu/zmianie sesji.
- Budowanie DOM przez `node`/`textContent`, bez `innerHTML` i bez przechowywania historii w localStorage.

Weryfikacja: `node --check web/dashboard.js`; testy `tests/test_b1501_financial_history.py` i `tests/test_b1561_financial_panel.py`.

Ograniczenia: brak rzeczywistych płatności, brak testów z przeglądarką i PostgreSQL; numeracja pakietu jest zakresem roboczym, nie liczbą funkcji.
