# WiejskaPaka: integracja API z PostgreSQL RLS

Kontynuacja PR #61. Przetestowany kod funkcjonalny: `1fe9f2c`, z końcowym kompletem testów `5a5a38f`.
Ten dokument zastępuje blokery integracji opisane w raporcie PR #61; historyczne
pliki `database/security_review/` pozostają projektem i nie są ścieżką wdrożenia.
Aktualna migracja: `database/security_rls/001_gateway.up.sql`, rollback: plik DOWN
w tym samym katalogu. Żadnego z tych plików nie uruchomiono na VPS ani produkcji.

## Granica autoryzacji

Konto SQL API nie ma bezpośrednich praw do tabel ani sekwencji. Uprawnieniem do
wykonania jest HMAC-SHA256 obejmujący dokładne zapytanie po bezpiecznym związaniu
parametrów, jego wynikowe typy, cel operacji, Bearer, nazwę bazy, PID połączenia,
identyfikator transakcji, termin ważności i jednorazowy nonce. Podpis wystawia
zaufany backend, nie klient HTTP. Samo hasło konta SQL lub token klienta nie
pozwala wykonać dowolnego zapytania ani zmienić salda.

`wp_rls.execute` sprawdza podpis, kontekst i zużycie nonce, rozpoznaje użytkownika
na podstawie ważnej sesji w bazie, a następnie wykonuje dokładnie podpisany SQL
jako ograniczona rola bez własności tabel i BYPASSRLS. Wszystkie tabele public
mają ENABLE + FORCE RLS oraz oddzielne polityki SELECT/INSERT/UPDATE/DELETE.
Polityki obejmują własność wiersza i relacje zamówienia, przesyłki, portfela,
dokumentu lub punktu. Reidentyfikacja właściciela zamówienia/przesyłki jest
odrzucona przez politykę UPDATE. Niezmienialne snapshoty finansowe zachowują
zakaz UPDATE/DELETE, istniejące CHECK, FK i triggery.

Podpisany SQL jest uprawnieniem nadanym przez kod serwera: poprawność biznesowa
zależy także od zachowanych kontroli ról, własności, stanów, PIN, idempotencji i
limitów w endpointach. Nie wolno udostępniać klientowi funkcji podpisującej SQL,
klucza ani możliwości wyboru celu `auth`/`maintenance`. Klucz jest autorytetem
serwera; przejęcie całego procesu lub klucza wraz z dostępem SQL wykracza poza
ochronę przed samym przejęciem hasła SQL. RLS nie zastępuje logiki biznesowej.

`actor_id`, `role`, `system=true` i dowolne podobne GUC nie stanowią dowodu
uwierzytelnienia. Zwykły kontekst jest przechowywany w prywatnej tabeli, do której
konto API nie ma dostępu. Dla transakcji tylko do odczytu używany jest pełny
podpisany dowód w SET LOCAL; polityka ponownie weryfikuje HMAC i związanie z
transakcją. Samodzielna zmiana tych parametrów nie daje żadnych praw. Po błędzie
rollback usuwa lokalny stan, a po poprawnym zapytaniu kontekst jest czyszczony.

Typy danych przechodzą przez tekstowy format PostgreSQL i oryginalne loadery
psycopg. BIGINT/grosze, NUMERIC/Decimal, NULL, JSON, boolean, daty i bytea nie są
zamieniane na stratne liczby float ani uszkadzane przez transport JSON.

## Włączenie do istniejących przepływów

- Middleware ASGI przekazuje kontekst każdego żądania do wszystkich routerów
  i połączeń synchronicznych. PgConnection podpisuje zapytania zarówno z db(),
  jak i z transakcji ponownie uwierzytelniających zapis.
- Rejestracja, logowanie, reset hasła, budżety prób i sesje mają ograniczony cel
  `auth` z możliwością działania przed ustanowieniem użytkownika. Tożsamość dla
  prywatnych operacji nadal pochodzi z sesji w bazie. Dotychczasowe sprawdzanie
  hasła, pojedyncze użycie resetu i odwołanie sesji pozostają zachowane.
- Zamówienia, przesyłki, dokumenty, portfele i wypłaty zachowują dotychczasowe
  transakcje. Konto SQL nie może ominąć ich przez bezpośredni INSERT/UPDATE.
- Dla kuriera adres jest dostępny tylko podczas aktywnej przydzielonej dostawy,
  przed PIN i potwierdzeniem. Sprzedawca widzi punkt odbioru albo dane jawnie
  udostępnione w obsługiwanym uzgodnieniu dostawy. Endpoint lokalizacji nadal
  zachowuje własne, bardziej szczegółowe reguły odpowiedzi i nie ujawnia adresu
  administratorowi. Bezpieczny odczyt samego pickup_point_id wspiera sprawdzanie
  dokumentu zakupowego sprzedawcy bez zwracania adresu dostawy.
- Start aplikacji, wygaszanie rezerwacji, retencja PIN, kolejki i zadania
  systemowe działają jako podpisany cel serwera `maintenance`. Nie istnieje
  klientowa flaga SQL pozwalająca uzyskać ten wyjątek. Workery i odbiornik SES
  sprawdzają ograniczoną rolę, chroniony schemat oraz dostęp do gateway.
- Savepointy, rollback, odczyt parametrów i ograniczone SET LOCAL timeoutów
  pozostają operacjami konta SQL; nie dają dostępu do danych. Diagnostyka
  READ ONLY działa bez zapisu do tabel kontekstu/nonce.
- Zadanie tygodniowe rozpoznaje PostgreSQL po adapterze, a nie po przypadkowej
  obecności DATABASE_URL, i zachowuje blokadę advisory oraz istniejący kalendarz.

Nie zmieniono prowizji, zaokrągleń, groszy, PIN, refundów, zakresu rzeczywistych
płatności ani reguł produktu. Dotychczasowa blokada WP_ENV production/prod/live
oraz niezależna blokada żądań testowych pozostają włączone.

## Role i sekrety

| Rola | Przeznaczenie |
|---|---|
| osobny administrator/migrator | instalacja ról, właściciele obiektów, kontrolowane migracje; nigdy konto procesu API |
| wp_rls_runtime | NOLOGIN, członkostwo tylko dla dedykowanego loginu API/workerów; USAGE schematu, EXECUTE gateway i bezpiecznego DESCRIBE; bez tabel i sekwencji |
| wp_rls_executor | NOLOGIN, bez członków i BYPASSRLS; właściciel gateway, DML przez RLS; brak DDL i dostępu do klucza |
| wp_rls_guard | NOLOGIN, bez członków i BYPASSRLS; właściciel ograniczonych funkcji weryfikujących i sprawdzających relacje; tylko SELECT potrzebny resolverom |
| wp_rls_backup | NOLOGIN, osobny login operatora backupu; SELECT pełnego snapshotu przez jawną politykę, bez DML i bez dostępu do wp_rls_keys |

Wszystkie role mają NOSUPERUSER, NOBYPASSRLS, NOCREATEDB, NOCREATEROLE,
NOREPLICATION. Login API musi dziedziczyć wyłącznie wp_rls_runtime; nie może być
członkiem wykonawcy, guard, backupu, migratora ani ról administracyjnych.
Kontrola startowa obejmuje także własność tabel, sekwencji, prywatnych funkcji
oraz CREATE w public i schematach zabezpieczeń. Właściciel może zmienić/wyłączyć
RLS mimo FORCE, dlatego nigdy nie może być loginem aplikacji.

Klucz 32 losowych bajtów jest przechowywany w prywatnym pliku JSON
`{"key":"<64 znaki hex wygenerowane przez secrets.token_hex(32)>"}` i osobno w
`wp_rls_keys.secrets`. Plik musi należeć do UID procesu, mieć 0600 i nie być
symlinkiem; katalog powinien mieć 0700. Konfiguracja API/workerów:
`WP_RLS_KEY_FILE=/bezwzgledna/prywatna/sciezka`, `WP_RLS_GATEWAY=1`.
Klucz i DSN migratora nie mogą trafić do repozytorium, przeglądarki ani logów.
DESCRIBE i wykonanie są wywołaniami z parametrami; literalny SQL zawierający PII
nie jest wysyłany jako widoczny PREPARE w pg_stat_activity.

Zainstalowany schemat RLS wymusza gateway także bez flagi. Brak schematu przy
skonfigurowanym RLS, brak klucza, niewłaściwy klucz lub niewłaściwa rola powodują
odmowę; nie ma automatycznego powrotu do starego dostępu.

## Odtworzenie odbioru lokalnego

1. Python 3.12, `pip install -r requirements-security-test.txt` w osobnym venv.
2. `python -m scripts.run_rls_api_gate --report work/rls-api.xml` tworzy nowy
   lokalny klaster PostgreSQL, losowe loginy/bazy, klucz i pełny zweryfikowany
   schemat. Włącza RLS PRZED uruchomieniem API. Każda baza fixture ma sprawdzone
   ENABLE + FORCE dla wszystkich tabel. Skrypt ignoruje produkcyjne DSN.
3. `python scripts/run_full_regression.py --timeout 360` uruchamia każdy moduł
   osobno. Do podziału na dwa procesy użyć --shard 1/2 oraz 2/2 i osobnych raportów.
4. `python -m scripts.check_browser_backend_bridge` — historyczny scenariusz
   poprawiony do obecnego interfejsu; prawdziwy Chromium i in-process FastAPI,
   bez udawania, że jest to sieciowy test HTTP. Sieciowy HTTP jest w bramie RLS.

Wyniki i pokrycie tras: `RLS_INTEGRACJA_WYNIKI_2026-11-15.json`. Zestawy mogą się
pokrywać; nie sumować ich jako odrębnych przypadków. Wyniki PR #61 bez RLS nie
stanowią już dowodu zgodności nowej integracji — liczy się aktualna brama RLS.

## Procedura przyszłego wdrożenia — NIE WYKONANO

1. Zatrzymać API i wszystkie workery, zamknąć pule. Na odizolowanym klonie
   potwierdzić zgodność pełnego manifestu tabel, funkcji, ról, ACL, default
   privileges i właścicieli. Zapisać obecny commit, konfigurację loginu oraz
   dokładne granty i członkostwa potrzebne do rollbacku. Przygotować sprawdzony
   backup z próbą odtworzenia. Nie używać konta API do instalacji.
2. Zweryfikować aktualny kod, kompletne PASS/FAIL/SKIP i bramę RLS. SQL UP ma
   blokadę procesu: operator dopiero po przeglądzie dowodów ustawia w sesji
   migracyjnej `SET wp_rls.api_compatibility_verified='yes'` i uruchamia plik UP
   z ON_ERROR_STOP. Jest to blokada przypadkowego wdrożenia, nie kryptograficzny
   dowód wykonania testów. Alternatywna flaga disposable_test działa wyłącznie
   dla nazw wp_test_* i jest używana przez fixture tworzące nowe bazy.
3. Jednorazowy administrator klastra instaluje ograniczone role/funkcje. Normalny
   login migracyjny pozostaje oddzielny. Nie nadawać SUPERUSER API, nie zmieniać
   private NOLOGIN na LOGIN i nie nadawać członkostwa w executor/guard.
4. Wygenerować nowy klucz lokalnie, zapisać z O_EXCL i 0600; umieścić identyczne
   bajty w `wp_rls_keys.secrets(singleton,key)` przez parametry psycopg z konta
   migracyjnego. Nie wpisywać wartości klucza w SQL/historii powłoki. Schemat
   bez klucza jest celowo niedostępny dla API.
5. Odebrać loginowi API jego dawne granty tabel/sekwencji i niepotrzebne grupy;
   nadać wyłącznie wp_rls_runtime z dziedziczeniem. Zweryfikować brak bezpośrednich
   grantów kolumnowych, właścicielstwa, CREATE i ról administracyjnych. PUBLIC
   nie może mieć CREATE w public. Oddzielić login backupu; ograniczyć CONNECT
   między bazami i nie używać globalnej roli backupu jako konta usługi/API.
6. Ustawić klucz i tryb RLS dla API oraz wszystkich workerów. Uruchomić nowy kod
   z nowymi połączeniami, wykonać sondy logowania, zamówienia, dokumentu, portfela,
   roli admin, sesji i workerów. Skontrolować odrzucenie dowolnego SQL kontem API,
   cofnięcie adresu po PIN i brak klucza w backupie. Na środowisku podobnym do
   docelowego zmierzyć opóźnienia i obciążenie; gateway dodaje rundy komunikacji.
7. Produkt nadal ma niezależną blokadę trybu produkcyjnego i brak rzeczywistego
   PSP. Zgodność RLS nie oznacza gotowości całej WiejskaPaka do produkcji.

W tej sesji nie wykonywano żadnego z tych kroków na VPS lub produkcyjnej bazie.

## Backup, odtworzenie i rollback

Backup używa osobnego konta wp_rls_backup, `pg_dump --enable-row-security` i
pełnej polityki SELECT dla tego konta. `wp_rls_keys` jest wykluczony z dumpa;
operator backupu nie ma do niego dostępu. Dane kontekstu/nonce również nie są
archiwizowane. Szyfrowanie archiwum, niezależny klucz opakowujący, kwarantanna
poczty i odwołanie sesji pozostają zachowane. Nie uruchamiać aplikacji bezpośrednio
na odtworzonym dumpie: --no-owner zmienia właścicieli SECURITY DEFINER. Próba
odtworzenia usuwa schematy wykonywania i stary wp_security, waliduje publiczne
dane wyłącznie offline, nie startuje API i usuwa tylko nowo utworzoną bazę próby.
Przyszłe przywrócenie wymaga ponownej instalacji gateway i świeżego klucza.

Rollback: zatrzymać API/workery i zamknąć połączenia. Wykonać DOWN z osobnej sesji
migracyjnej i ON_ERROR_STOP. Przywraca zapisane ENABLE/FORCE i usuwa tylko własne
polityki; odmawia, jeśli po wdrożeniu dodano nieznaną politykę. Nie usuwa danych
public. Wspólne role NOLOGIN są pozostawiane, ponieważ mogą być używane przez
inne bazy. Ich usunięcie wymaga osobnego audytu klastra, bez DROP OWNED/CASCADE
na cudzych obiektach.

Przywrócić poprzedni kod, jawnie zapisane granty/login bez praw administracyjnych
oraz konfigurację sprzed RLS; usunąć nową konfigurację klucza tylko po odłączeniu
od zabezpieczonego schematu. DOWN sam nie przyznaje dawnych szerokich praw API.
Nie odtwarzać całej bazy w celu cofnięcia polityk i nie resetować sald. Sprawdzić
login/logout/reset, izolację kont, PIN, refundy, dokumenty i kolejki. Rotacja
klucza: kontrolowane zatrzymanie usług, aktualizacja DB i atomowa podmiana pliku,
restart połączeń oraz sondy; nie utrzymywać mieszanych kluczy z cichym fallbackiem.


## Końcowe wyniki i zamknięcie PR #61

| Zestaw | PASS | FAIL | SKIP |
|---|---:|---:|---:|
| Pełna regresja, 394 moduły / 5030 przypadków | 4926 | 0 | 104 |
| Kompletny odbiór z RLS i FORCE RLS | 142 | 0 | 0 |
| PostgreSQL przed migracją, zachowanie trybu przejściowego | 95 | 0 | 0 |
| Sondy środowiska PostgreSQL | 2 | 0 | 0 |
| Rozszerzone role Chromium z mock API, 12 scenariuszy | 4 | 0 | 0 |
| Naprawiony bridge Chromium → FastAPI, 88 rzeczywistych żądań | PASS | 0 | 0 |

Bramę RLS stanowią 93 dotychczasowe przypadki API, cztery nowe rozbudowane
scenariusze HTTP i 45 prób SQL/autoryzacji/rollbacku. Wywołano wszystkie 140 tras:
139 ma zaobserwowane 2xx, a ręczny scheduler poprawnie odmawia 409 poza
poniedziałkiem. Dodatkowy test wykonuje rzeczywisty, idempotentny przebieg
poniedziałkowego zadania na PostgreSQL z RLS, bez przelewu. Nie osłabiono
reguły kalendarza, by uzyskać sztuczne 200.

Osobne przebiegi uzupełniły 102 ze 104 pominięć pełnego zestawu. Efektywnie
zweryfikowano **5028 PASS / 0 FAIL / 2 SKIP** jego unikalnych przypadków. Dwa
pominięcia dotyczą wyłącznie odmowy pracy z kluczami na systemie nie-POSIX;
środowisko jest Linux/POSIX. Zestawy częściowo się pokrywają: 45 prób SQL jest
również w pełnej regresji, a 93 przypadki API uruchomiono w obu trybach. Nie
sumować wszystkich wierszy jako niezależnych testów.

W obu częściach regresji complete=true, sources_unchanged=true, fingerprint
aplikacji zgodny z końcowym kodem, a hashe każdego modułu testowego zweryfikowano.
Po naprawie atrapy dawnego połączenia (pole gateway=False) i warunków Playwright
zgodnych z CSP powtórzono zmienione moduły, bez osłabiania ich asercji. Nie
wykorzystano przestarzałego PASS po zmianie pliku. pip check i git diff --check
przechodzą. Dokładne wyniki per moduł, per przypadek bramy i per trasa są w JSON.

Blokery PR #61 dotyczące pre-auth, DML, sesji, kontekstu wszystkich połączeń,
workerów i starego scenariusza Chromium zostały zamknięte w lokalnych testach.
W trybie przejściowym baza bez schematu/config RLS nadal działa jak wcześniej;
samo wdrożenie kodu nie jest włączeniem RLS. Instalacja schematu lub jawna
konfiguracja wymuszają nowy tryb bez cichego fallbacku.

Pozostaje przegląd niezależnego recenzenta i rzeczywistej konfiguracji ról/ACL,
kluczy, backupu oraz wydajności na klonie środowiska docelowego. Klucz podpisujący
jest autorytetem serwera i wymaga ochrony/rotacji. Nie testowano RLS na innych
wersjach/systemach niż lokalny PostgreSQL 16.2/Linux. Potwierdzono zgodność API
z RLS w tym środowisku; nie deklaruje to gotowości całego produktu do produkcji.
Nie wykonano wdrożenia ani żadnej zmiany VPS/produkcyjnej bazy.
