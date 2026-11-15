# PostgreSQL i autoryzacja — pakiet do przeglądu, 15.11.2026

Status: **NIE WDRAŻAĆ RLS do istniejącej aplikacji**. Paczka zawiera aktywne
zabezpieczenia procesu API oraz wykonujący się na PostgreSQL projekt RLS.
Nie jest ukończoną integracją aplikacji z RLS. Nie zmieniono VPS ani produkcyjnej bazy.

## Model zaufania i role

- `wp_migrator`: NOLOGIN, NOSUPERUSER, NOBYPASSRLS, bez tworzenia ról/baz i replikacji.
  Docelowy właściciel obiektów. Dedykowany login migracyjny może przyjmować tę rolę;
  jego sekret nie może znajdować się w środowisku API. Uprawnienia administratora
  wymagane są wyłącznie do jednorazowego utworzenia ról i transferu własności.
- `wp_runtime`: grupa NOLOGIN o tych samych ograniczeniach. Dedykowany login API
  dziedziczy tylko tę grupę, bez członkostwa w migratorze, właścicielach,
  `pg_read_all_data`, `pg_write_all_data`, `pg_execute_server_program` ani innych
  rolach administracyjnych. Nie posiada tabel, sekwencji, widoków ani CREATE w public.
- `wp_authenticator`: NOLOGIN, bez BYPASSRLS; wyłącznie właściciel dwóch funkcji
  SECURITY DEFINER, z SELECT określonych kolumn users/sessions. Jawne polityki
  SELECT umożliwiają rozpoznanie sesji przed ustanowieniem kontekstu. Nigdy nie
  nadawać członkostwa tej roli loginowi aplikacji.

Start API odrzuca role superuser, BYPASSRLS, CREATEDB, CREATEROLE, REPLICATION,
również osiągalne przez członkostwo, oraz własność relacji i CREATE w public.
Własność jest zabroniona także przy FORCE RLS: właściciel może wyłączyć RLS.
Kontrola nie jest pełnym audytem wszystkich funkcji/grantów z istniejącej bazy.
Przed przyznaniem roli sprawdzić także pg_auth_members, ACL baz/schematów,
SECURITY DEFINER, default privileges i uprawnienia PUBLIC. Nowe role same nie
usuwają uprawnień z istniejących loginów.

## Tożsamość bez możliwości podmiany actor_id

`neon_identity.authenticated_actor` i obecne polityki z neon_rls_policy_plan są
historycznym szkicem: custom GUC z ID jest dowolnie zapisywalny i nie stanowi dowodu
uwierzytelnienia. Nie wolno ich używać do ochrony SQL przed podszyciem.

Nowy `rls_session_context.session_context` ustawia SET LOCAL surowego Bearera, a
`wp_security.actor_id()` sam haszuje token w PostgreSQL i sprawdza aktywną sesję.
Identyfikator i rola pochodzą z bazy; GUC actor_id i role są ignorowane. Hash sesji
nie jest akceptowany zamiast tokenu. Resolver działa bez wcześniej ustalonego ID.
Funkcje mają stały search_path=pg_catalog, kwalifikowane nazwy tabel, odebrane
EXECUTE od PUBLIC oraz ograniczonego właściciela. Token ma istniejącą losowość
sesji aplikacji. Nie zmienia to zasad ważności sesji i wylogowania.

Nie zapisuj Bearera w logach SQL, parametrach diagnostycznych, APM i raportach.
Używaj wyłącznie transakcji żądania, z rollback po błędzie i bez session-level SET.
Wyciek ważnego tokenu nadal pozwala przejąć jego sesję. RLS nie chroni przed
przejęciem całego procesu API, kradzieżą haseł ani posiadaniem roli migracyjnej.

## Polityki i wyjątki systemowe

002 tworzy cztery polityki (SELECT, INSERT, UPDATE, DELETE) na każdej istniejącej
niekatalogowej tabeli public. Nierozpoznane tabele mają domyślną odmowę. Wykaz
wyjątków katalogowych jest jawny w SQL. Nieznane istniejące polityki przerywają
całą transakcję zamiast łączyć się w sposób poszerzający dostęp.

SELECT: klient i sprzedawca widzą swoje zamówienia; kurier tylko przydzielone,
wysłane, niepotwierdzone zamówienia; admin widok audytowy zamówień. Adresy są
bardziej restrykcyjne: klient swoje, sprzedawca tylko odbiór, kurier wyłącznie
aktywną dostawę. Admin nie otrzymuje automatycznie dostępu do adresu. Oddzielne
predykaty obejmują przesyłki, dokumenty zakupowe, portfele, wypłaty, powiadomienia
oraz dane sprzedawcy. Nie każda polityka SELECT daje grant: powierzchnia SQL
świadomie pozostaje minimalna do czasu integracji poszczególnych przepływów.
Grant kolumnowy orders nie obejmuje pin_hash; users nie obejmuje password_hash;
runtime nie otrzymuje SELECT sessions/token_hash.

INSERT/UPDATE/DELETE są **odmową**, także dla właściciela wiersza i administratora
aplikacyjnego. Nie wolno dopuścić arbitralnych zapisów do pieniędzy, PIN, właścicieli
zamówień i dokumentów. To projekt ograniczenia SQL, nie zamiennik istniejącej
logiki biznesowej. Konieczne są wąskie, osobno testowane procedury operacji
biznesowych przed aktywacją RLS. Wyjątek resolvera to wyłącznie SELECT sessions/users.
Nie dodano ogólnego `system=true`, GUC admin ani roli BYPASSRLS do pracowników.
Zadania rezerwacji, poczty, uzgodnień i wypłat wymagają osobnych loginów oraz
procedur z minimalnymi grantami — obecnie nie mają wyjątku omijającego ochronę.

## Wdrożenie kontrolowane

1. Zbudować odizolowany klon bez sekretów i danych osobowych produkcji. Zweryfikować
   wersję PostgreSQL i pełny manifest istniejących migracji; wykonać backup i próbę
   odtworzenia. Nie używać produkcyjnego DATABASE_URL do testów.
2. Przejrzeć raport audytu i wyniki testów. Aktywne zmiany API można testować bez
   RLS. Nowa kontrola konta PostgreSQL wymaga uprzedniego rozdzielenia loginu
   migracyjnego i aplikacyjnego; właściciel bazy nie jest poprawnym loginem API.
3. Wyłącznie w klonie, dedykowanym administratorem uruchomić z ON_ERROR_STOP:
   `database/security_review/001_roles.up.sql`. Nie podłączać jeszcze API przez
   wp_runtime. Te pliki celowo nie należą do automatycznego manifestu migracji.
4. Zintegrować logowanie/rejestrację/reset hasła przez ograniczone funkcje
   bootstrap (obecne zapytania SELECT * users i sessions nie są kompatybilne).
   Zintegrować wszystkie odczyty z kontekstem sesji oraz zapisy i zadania z
   dedykowanymi procedurami. Usunąć SELECT * z powierzchni runtime.
5. Przetestować pełne API i browser na klonie **z włączonym RLS**, cztery role,
   utratę uprawnień sesji, checkout/PIN/refundy/wallet/wypłaty, restart, współbieżność
   i workers. Zachować prowizje, grosze, PIN i zwroty. Obecne testy API bez RLS nie
   stanowią tego potwierdzenia.
6. Dopiero po udokumentowaniu zgodności z pkt 5, w tej samej kontrolowanej sesji
   ustawić `SET wp_security.compatibility_verified='yes'` i wykonać
   `database/security_review/002_rls.up.sql`. Zmienna jest blokadą procesu, nie
   kryptograficznym dowodem zaliczenia testów. Testy migracji ustawiają ją tylko
   w świeżym lokalnym klastrze. **Nie ustawiać jej teraz na VPS.**
7. Transfer własności i granty dedykowanego loginu wykonać według zatwierdzonego
   inwentarza ACL; zapisać poprzednie owner/ACL i role. Nie podawać haseł w repo.
   Nie rozszerzać grantów do ALL w celu usuwania błędów kompatybilności.

## Wycofanie

Zatrzymać ruch i zadania, zamknąć/podmienić pule połączeń. Wycofać zmianę loginu
API do poprzednio zweryfikowanego loginu nieadministracyjnego. Wykonać kolejno
002_rls.down.sql i 001_roles.down.sql z ON_ERROR_STOP. 002 przywraca zapisane
flagi ENABLE/FORCE i usuwa wyłącznie własne polityki; migracja UP odmawia przy
wcześniejszych politykach. Nie odtwarzać bazowych tabel ani nie usuwać danych.
Jeżeli login został już członkiem nowych ról lub zmieniono ownership, najpierw
cofnąć te osobne operacje z zapisanego inwentarza; DROP ROLE celowo odmówi przy
pozostawionych zależnościach. SQL DOWN nie usuwa rozszerzeń ani kont użytkowników.

Kod API można wycofać przez revert commitu po przeglądzie wpływu utraty nowej
blokady. Nie uruchamiać produkcji po wycofaniu zabezpieczeń. Po rollbacku sprawdzić
login, wylogowanie, brak cudzych zamówień/adresów, kolejki, integralność groszy i
niezmienność dokumentów. Nie wykonywać automatycznych napraw sald.

## Odtwarzanie testów

Zainstalować requirements-lock.txt w izolowanym venv. Dodatkowy opcjonalny pakiet
`pgserver==0.1.4` służy tylko testom świeżego lokalnego PostgreSQL; test nie przyjmuje
DATABASE_URL i używa nowego klastra w tmp. Weryfikować wersję pakietu w raporcie.

- `python scripts/run_full_regression.py --timeout 180` — każdy moduł osobno.
- `python -m pytest -q tests/test_rls_security_postgres.py` — role, RLS, podszycie,
  adresy, kolumny, brak zapisu, wycofanie migracji.
- `python scripts/run_tests_isolated.py -q tests/test_security_environment_boundary.py tests/test_postgres_runtime_role.py`.
- Istniejące `tests/test_postgres_full_api_optin.py`: wyłącznie nowy lokalny klaster
  testowy z WP_TEST_POSTGRES_DSN, nigdy produkcja. To test bieżącego API **bez RLS**.
