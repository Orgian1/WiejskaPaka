# WiejskaPaka — pakiety B/41–B/45

Test integracyjny `python -m scripts.check_browser_backend_bridge` uruchamia Chromium, interfejs JavaScript i prawdziwy backend FastAPI na tymczasowej bazie SQLite, przekazując żądania przez most w procesie (bez połączenia sieciowego HTTP).

- B/41: anulowanie zamówienia z dostawą z poziomu panelu klienta.
- B/42: powtórne anulowanie zwraca 409 i nie przywraca magazynu po raz drugi.
- B/43: zakup ilości przekraczającej stan magazynowy jest odrzucany bez zmiany stanu.
- B/44: rolnik oznacza odbiór jako gotowy; błędny PIN zużywa jedną z pięciu prób.
- B/45: prawidłowy PIN po zaznaczeniu kontroli towaru potwierdza odbiór; ponowne użycie PIN-u zwraca 409.

Scenariusz obejmuje 79 rzeczywistych żądań do backendu przez most testowy. Nie testuje prawdziwego HTTP, PostgreSQL, RLS ani płatności produkcyjnych. Baza Neon i strona publiczna pozostają nietknięte.
