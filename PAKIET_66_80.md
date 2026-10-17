# WiejskaPaka — duży pakiet 66–80: audyt PostgreSQL i testy zgodności

## Wprowadzone zmiany
- Naprawiono obsługę rekordów `dict_row` psycopg 3 w `neon_rls_preflight.py` i `neon_security_audit.py`. Poprzednie wersje indeksowały wyniki jak krotki, przez co audyt na PostgreSQL mógł kończyć się błędem.
- Nadano alias `policy_count` kolumnie obliczeniowej, aby można ją było odczytać po nazwie.
- Dodano testy regresyjne obejmujące słownikowe wyniki bazy oraz ocenę wyłączonego RLS.
- Dodano opcjonalny, **tylko do odczytu** test połączenia ze stagingowym PostgreSQL (`tests/test_postgres_live_opt_in.py`). Domyślnie jest pomijany. Nie używać danych produkcyjnych ani uprawnień właściciela.

## Granice ukończenia
Numer 66–80 to oznaczenie dużego pakietu prac, a nie twierdzenie, że 15 niezależnych funkcji jest gotowych. RLS nie został włączony. Nie testowano połączenia z bazą Neon użytkownika. Nie podłączono płatności, nie zmieniono publicznej strony.

## Co jeszcze jest konieczne
1. Uruchomić testy na izolowanym PostgreSQL i sprawdzić schemat, zapytania, migracje oraz autoryzację.
2. Przejrzeć polityki RLS, rolę DB, sposób obsługi sesji i wszystkie ścieżki zapisu; dopiero po testach wdrażać zmiany na staging.
3. Testy przepływów użytkowników i dostaw, w tym prywatności, PIN, anulowania i zwrotów.
4. Integracja operatora płatności i zgodności prawnej dopiero po decyzjach biznesowych.
