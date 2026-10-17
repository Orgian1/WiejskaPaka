# Pakiet A — obsługa błędów transakcji PostgreSQL

## Zmiana
W `backend/neon_identity.py` poprawiono sprzątanie transakcyjnego kontekstu tożsamości. Gdy zapytanie w obrębie `authenticated_actor` kończy się błędem i PostgreSQL oznacza transakcję jako przerwaną, próba wykonania SQL czyszczącego kontekst może także zakończyć się błędem. Teraz oryginalny wyjątek nie jest maskowany przez wtórny błąd sprzątania. Jeśli sprzątanie zawiedzie po udanej operacji, błąd pozostaje widoczny i transakcja musi zostać wycofana przez jej właściciela.

## Testy
Dodano `tests/test_identity_cleanup_failure.py` (2 testy). Pełny lokalny zestaw: **2404 passed, 6 skipped, 16 subtests passed**.

## Ograniczenia i warunki wdrożenia
Nie przeprowadzono rzeczywistych testów PostgreSQL/Neon; 6 testów pominięto. Mechanizm wymaga zarządzania transakcją przez `postgres_db` i nie jest samodzielną ochroną RLS. RLS nadal wyłączony. Nie podłączono produkcyjnych płatności i nie zmieniono publicznej witryny.
