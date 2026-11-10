# Audyt 03 — równoległe zdarzenia płatności testowych

## Zmiana
`backend/payment_store.py`: zapis stanu symulowanej płatności używa warunkowej aktualizacji (compare-and-swap) obejmującej dotychczasowy stan, kwotę zwrotu i kwotę wypłaty. Gdy wiersz zmienił się pomiędzy odczytem a zapisem, operacja zgłasza błąd zamiast nadpisywać nowy stan. Wyjątek wymaga wycofania całej transakcji przez wywołującego.

## Testy
`tests/test_payment_concurrency_audit03.py` sprawdza powtórzone zdarzenia, kolizję identyfikatora między zamówieniami, zapis ze starego stanu oraz dwóch równoległych autorów zmiany w SQLite (`BEGIN IMMEDIATE`).

Pełny lokalny zestaw: **2366 passed, 4 skipped, 16 subtests passed** na świeżej bazie SQLite. Nie wykonywano testów PostgreSQL ani Neon.

## Ograniczenia
- Mechanizm dotyczy **wyłącznie symulacji**; brak prawdziwych płatności i zwrotów.
- PostgreSQL musi zostać przetestowany osobno pod kątem izolacji transakcji, blokad i ponawiania operacji.
- Warunkowy UPDATE nie zastępuje blokady wiersza (`SELECT ... FOR UPDATE`) i unikalności identyfikatorów zdarzeń w bazie.
- RLS pozostaje wyłączony; aplikacja nie jest gotowa do wdrożenia produkcyjnego.
- Nie modyfikowano bazy Neon ani strony wiejskapaka.pl.
