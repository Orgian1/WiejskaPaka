# WiejskaPaka — zbiorczy pakiet 19–22

## Faktyczne zmiany
- `GET /orders/me`: przy konfiguracji PostgreSQL ponownie weryfikuje nagłówek Bearer wewnątrz transakcji używanej do pobrania zamówień; identyfikator aktora pochodzi wyłącznie z sesji, a rola jest ponownie odczytywana z `users`. Zapytania filtrują po `buyer_id` lub `farmer_id`.
- `GET /couriers/me/active-addresses`: przy konfiguracji PostgreSQL analogicznie weryfikuje sesję i rolę w transakcji, a adresy filtruje według przypisanego kuriera, statusu `w_drodze_testowo`, niewykorzystanego PIN i braku potwierdzenia. Nie zwraca numerów telefonów.
- SQLite zachowuje dotychczasową ścieżkę obsługi obu endpointów.
- Dodano sześć testów regresyjnych PostgreSQL z atrapami połączenia, obejmujących filtrowanie po aktorze z sesji, odmowę dla innych ról oraz nieważną sesję.

## Weryfikacja
`python -m pytest -q`: **1287 passed, 3 skipped, 16 subtests passed** (lokalnie, bez połączenia z Neon).

## Ograniczenia i ryzyka
- Pozostałe endpointy nadal korzystają ze starego mechanizmu `current_user`/`db`. Nawet w dwóch zmienionych endpointach FastAPI wykonuje `current_user` jako zależność przed wejściem do nowej transakcji — pełna konsolidacja uwierzytelniania pozostaje do wykonania.
- RLS pozostaje wyłączony. Wspólne konto SQL i custom GUC nie stanowią samodzielnej ochrony przed kompromitacją połączenia.
- Nie testowano prawdziwego PostgreSQL/Neon ani polityk RLS; testy używają atrap.
- Nie modyfikowano Neon, strony wiejskapaka.pl ani płatności produkcyjnych.

## Dalsze prace bez zatwierdzania każdego kroku
Przenieść pozostałe odczyty i zapisy do spójnego modelu transakcyjnego, wyeliminować podwójną weryfikację sesji, przygotować izolowaną integrację PostgreSQL i dopiero po testach zaplanować włączenie RLS.
