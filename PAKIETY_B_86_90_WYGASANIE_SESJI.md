# B/86–B/90 — wygasanie i unieważnianie sesji

- B/86: sesja z datą ważności w przeszłości nie odczytuje zamówień.
- B/87: wygasła sesja nie może wylogować innych urządzeń.
- B/88: błędny schemat nagłówka Authorization i zmodyfikowany token są odrzucane.
- B/89: nowe logowanie po wygaśnięciu tworzy odrębny, działający token.
- B/90: wylogowany token nie odzyskuje ważności po nowym logowaniu.

Testy korzystają z izolowanej SQLite oraz rzeczywistych endpointów FastAPI. Nie stanowią audytu PostgreSQL, Neon ani RLS. Płatności pozostają testowe.
