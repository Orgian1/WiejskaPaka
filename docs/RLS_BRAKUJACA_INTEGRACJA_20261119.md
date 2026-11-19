# WiejskaPaka — kontrola obecności RLS na gałęzi roboczej, 19.11.2026

## Wynik kontroli repozytorium
Sprawdzono drzewo Git gałęzi `feat/zatwierdzony-widok-gwiazdki-reklamy-rls-20261118` na commicie `d4b4d557` i dokument `docs/PLAN_INTEGRACJI_ZATWIERDZONY_WYGLAD_RLS_REKLAMY_20261117.md`.

**Brak w bieżącym drzewie plików integracyjnych wskazanych w planie:**
- `backend/rls_gateway.py`
- `backend/rls_session_context.py`
- `database/security_rls/`
- `scripts/run_rls_api_gate.py`

Obecne są `backend/neon_rls_policy_plan.py` i `backend/neon_rls_preflight.py`, ale pierwszy jest wyłącznie projektem polityk SELECT, a drugi tylko odczytuje status bazy. Żaden z nich sam nie wdraża ochrony RLS.

## Wniosek
Nie należy deklarować, że FORCE RLS działa w bieżącym demo. Nie wykonano tu połączenia z rzeczywistym PostgreSQL ani nie potwierdzono stanu polityk bazy. Wyniki testów SQLite i zatwierdzonego interfejsu nie zastępują testów ról i polityk.

## Następny bezpieczny etap
1. Odszukać i zweryfikować kod RLS z gałęzi źródłowej `WIEJSKAPAKA-FINAL-WYGLAD-RLS-REKLAMY-20261116`.
2. Przenieść **selektywnie** zgodne moduły backendu, migracje i testy; nie kopiować ani nie podmieniać zatwierdzonych plików widoku.
3. Dopasować integrację do aktualnego `backend/app.py` i adaptera PostgreSQL, bez automatycznego włączania RLS.
4. Uruchomić testy izolacji kont na odizolowanym PostgreSQL, w tym wymuszone FORCE RLS, próby odczytu cudzych zamówień, PIN i adresów.
5. Dopiero po potwierdzeniu wszystkich bram i osobnej zgodzie rozważyć migracje na środowisku docelowym.

**Nie wdrażano niczego na VPS, nie aktywowano PayU, nie zmieniano zatwierdzonego interfejsu.**
