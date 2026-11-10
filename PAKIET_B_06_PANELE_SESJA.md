# Pakiet B/06 — panele rolnika i administratora, ochrona sesji

- Panel rolnika: odpowiedź z raportem rozliczeń (również błąd) nie aktualizuje interfejsu po zmianie sesji.
- Panel rolnika: odpowiedzi operacji wysyłki i przypisania kuriera nie wyświetlają komunikatów po wylogowaniu.
- Panel administratora: spóźniona odpowiedź raportu nie pojawia się po wylogowaniu; kolejny raport zastępuje poprzedni zamiast tworzyć wiele kart.
- Powiadomienia: po oznaczeniu jako przeczytane nie wykonuje się odświeżenie danych dla starej sesji.
- Dodano cztery testy regresyjne; składnia JS sprawdzona `node --check`.
- Testy lokalne: 2429 zaliczonych, 6 pominiętych, 16 podtestów zaliczonych.

Ograniczenia: testy sprawdzają kod i lokalne działanie, nie zastępują testów w przeglądarce telefonu. Nie uruchomiono rzeczywistego PostgreSQL, nie włączano RLS, nie podłączano płatności. Neon i publiczna strona bez zmian.
