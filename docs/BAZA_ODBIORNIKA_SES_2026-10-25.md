# Chroniona baza testowa odbiornika SES — bez uruchomienia usługi

Gałąź preview/ses-feedback-database-20261025. Nowy moduł jest osobnym adapterem
konfiguracji i połączeń. Brak zmiany VPS, zasobów AWS, prawdziwych poświadczeń,
SMTP, migracji, uruchamiania HTTP lub podłączenia do głównej aplikacji.

## Plik i zakres

`backend.ses_feedback_database` czyta istniejący plik POSIX poza repozytorium:
zwykły plik, właściciel procesu, bez dostępu grupy/innych, bez symlinku końcowego,
z kontrolą fstat, O_NOFOLLOW/O_NONBLOCK i limitem 16 KiB. Nie tworzy pliku.
Ścisły dokument JSON ma dokładnie format=1, purpose=`ses-feedback-database-v1`
i connection. Mapa connection ma dokładnie: host, port (int), database, user,
password oraz sslmode. Nie są akceptowane DSN z dodatkowymi parametrami,
service, hostaddr, options ani nieznane pola. Duplikaty JSON są odrzucane.

Obsługiwane adresy: wyłącznie 127.0.0.1 lub ::1, port 1–65535, jawny użytkownik
i niepuste hasło. Nazwa bazy: wp_test_* albo wiejskapaka_test[_*], do 63 znaków,
wyłącznie litery/cyfry/podkreślenia po wymaganym prefiksie. Produkcyjne nazwy,
localhost/DNS, multihost i adresy zewnętrzne są odrzucane. sslmode musi być
jawnie disable, require, verify-ca lub verify-full. To wariant lokalnej bazy
TESTOWEJ; nie dodano konfiguracji produkcyjnego odbiornika.

Nazwa i loopback nie dowodzą, że baza nie zawiera rzeczywistych danych ani że
port nie jest przekierowaniem. Operator nadal odpowiada za wskazanie właściwego
środowiska. Wszystkie wartości są polami połączenia, nie fragmentami SQL.

`WP_ENABLE_SES_FEEDBACK_DATABASE=0` domyślnie. Flaga `1` wymaga WP_ENV=test/testing
i ścieżki WP_SES_FEEDBACK_DATABASE_FILE. Niepuste zmienne PG* są odrzucane przy
ładowaniu konfiguracji oraz ponownie bezpośrednio przed każdym połączeniem.
Wczytanie pliku nie otwiera DB ani sieci; snapshot parametrów jest niezmienny,
bez sekretów w repr. Przykład env nie zawiera hasła.

## Sprawdzenie tego samego połączenia

Target tworzy nowe połączenie PostgreSQL z connect_timeout=5, jawnym hostaddr
równym zatwierdzonemu adresowi oraz stałymi opcjami: statement_timeout=5s,
lock_timeout=1s, idle_in_transaction_session_timeout=10s,
search_path=pg_catalog,public,pg_temp. Nie używa połączenia globalnego/puli.

Przed zwróceniem połączenia przeprowadza na nim transakcję READ ONLY:
- rzeczywista nazwa bazy musi odpowiadać zatwierdzonej;
- rolsuper, rolbypassrls, rolcreaterole i rolcreatedb muszą być false;
- wymagany USAGE schematu public i domyślne writable transakcje przyszłej sesji;
- muszą istnieć publiczne tabele ses_feedback_events, ses_feedback_review,
  mail_recipient_blocks;
- wymagane SELECT/INSERT dla trzech tabel, UPDATE blokad oraz DELETE archiwum.

Błąd zamyka połączenie i daje wyłącznie SES_FEEDBACK_DATABASE_REJECTED. Po
poprawnym zakończeniu sondy zwracane jest to samo połączenie, gotowe na własną
transakcję odbiornika. Nie ma DDL, zapisu danych ani migracji podczas sondy.
Kontrola nie jest pełnym audytem członkostw roli, właścicielstwa, RLS, kolumn,
constraintów lub pochodzenia danych. Timeouty są limitami połączenia/zapytań;
kilka kolejnych zapytań może łącznie trwać dłużej niż pojedynczy limit 5 sekund.

## Jawna komenda kontrolna

`python -m scripts.check_ses_feedback_database` domyślnie zwraca DISABLED, bez
czytania pliku i DB. `--connect` pozwala wyłącznie na chroniony odczyt konfiguracji,
sondę oraz zamknięcie połączenia. Wynik to DISABLED, DATABASE_VALID albo
DATABASE_REJECTED (exit 1). Nie ma nazwy bazy, hosta, hasła ani tekstu wyjątku
w JSON. DATABASE_VALID nie sprawdza pinów, kluczy archiwum, AWS ani dostarczania.
Nie uruchamia listenera i nie stanowi zgody na publikację.

## Walidacja i kontynuacja

177/177 lokalnie, bez błędów/pominięć, 9 izolowanych modułów. Po dodaniu trzech
przypadków odrzucenia środowiska powtórzono zmieniony moduł; pozostałe wyniki
zachowano tylko dla niezmienionych hashy źródeł/testów. W tym 38 testów nowego
adaptera/komendy: zakres konfiguracji, prywatne pliki, bezczynność domyślna,
sonda na tej samej sesji, odrzucenie faktycznej złej bazy/roli/tabel/uprawnień,
odrzucenie odziedziczonego routingu przed połączeniem i redakcja błędów.
Testy jednostkowe sondy korzystają z fake drivera, nie są dowodem wykonania PG.

Nowy native test ładuje prywatny plik z danymi jednorazowej bazy CI, sprawdza
rzeczywisty statement_timeout, używa Target w fabryce HTTP i odczytuje dziennik
po 204 z osobnego połączenia. Lokalnie tylko kolekcja: 70 testów w module native;
faktyczne wykonanie nowego przypadku PostgreSQL 16/17 wymaga CI tej gałęzi.

Poprzednik PR #38/run 40176160058: PostgreSQL 16/17, Chromium, szybki Windows oraz
osobny krok Synthetic SNS HTTP boundary diagnostics SUCCESS; pełny Windows
podczas kontroli nadal IN_PROGRESS. Nie przenosić tego wyniku na nowy kod.
Dowody: docs/audits/feedback_database_2026-10-25/.

Dalej: CI, połączenie snapshotów pinów/kluczy/Target z kontrolą zachowanych
rekordów w przygotowaniu procesu, operacyjny launcher, HTTPS/proxy, rzeczywiste
piny i uprawnienia SNS, procedura subskrypcji, monitoring oraz retencja.
