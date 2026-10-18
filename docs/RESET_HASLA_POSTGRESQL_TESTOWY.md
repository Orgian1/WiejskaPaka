# Reset hasła na PostgreSQL — prywatny test

Rozszerzenie protokołu resetu na lokalny PostgreSQL. Nie podłącza SMTP,
nie wysyła e-maili i nie weryfikuje własności adresu. Służy wyłącznie
syntetycznym kontom w zamkniętym środowisku testowym POSIX.

## Jawne włączenie

Domyślnie reset na PostgreSQL pozostaje wyłączony. Potrzebne są jednocześnie:

- WP_ENV=test (lub testing);
- WP_ENABLE_TEST_PASSWORD_RESET=1;
- WP_ENABLE_PG_TEST_PASSWORD_RESET=1;
- WP_TEST_RESET_OUTBOX wskazujący bezwzględny prywatny katalog poza projektem;
- DATABASE_URL wskazujący loopback/localhost i bazę wp_test_* lub *_test.

Zdalny host, konfiguracja usług libpq, odziedziczone zmienne routingu,
tryb produkcyjny oraz publiczna/dowiązana skrzynka są odrzucane.
Nie podawać haseł w repozytorium lub czacie. Launchery demonstracyjne i
runner izolacji usuwają odziedziczoną konfigurację tego trybu. Natywna bramka
włącza go wyłącznie w osobnym fixture na nowej losowej bazie i roli.

Tabele password_reset_tokens i password_reset_limits muszą pochodzić
z zatwierdzonego pakietu migracji. Start API nie tworzy ich na PostgreSQL.
Sama flaga WP_ENABLE_TEST_PASSWORD_RESET nie odblokowuje tego wariantu.

## Ochrona współbieżności

Transakcje wydania i potwierdzenia linków korzystają z blokady doradczej
PostgreSQL dla limitów resetu. Operacje na konkretnym koncie biorą następnie
tę samą blokadę adresu, której używają logowanie i zwykła zmiana hasła.
Po oczekiwaniu ponownie odczytywana jest wersja hasła związana z linkiem.

Dzięki temu kilka procesów API nie zużyje jednego linku wielokrotnie ani
nie ominie limitu 3 wiadomości na adres w 15 minut. Przy wyścigu z logowaniem
starym hasłem sesja utworzona przed resetem jest cofana; logowanie po zmianie
nie może uwierzytelnić starego hasła. Potwierdzenie cofa wszystkie sesje i
linki resetu konta. Błąd bazy wycofuje zmianę hasła, sesji i tokenów razem.

Globalny limit demo wynosi 100 żądań wydania oraz 100 prób potwierdzenia
na 15 minut. To ograniczenie środowiska testowego, nie docelowe rozwiązanie
wysyłek dla 500000 klientów. Nie zmieniono reguł zakupów, PIN-ów lub rozliczeń.

## Odbiór

Nowe scenariusze natywne sprawdzają reset i ponowienie po restarcie,
odszyfrowywanie dotychczasowych zakupów z zachowanym kluczem,
równoległe wydania i potwierdzenia, wyścig ze starym logowaniem oraz
uwierzytelnioną zmianą hasła. Wstrzyknięty błąd DELETE sesji sprawdza rollback.
Wynik CI jest osobnym dowodem; lokalne SKIP nie jest wykonaniem PostgreSQL.

Prywatne pliki wiadomości zawierają tokeny i nie mogą być serwowane przez
HTTP, dodawane do Git, logów, artefaktów CI lub zwykłych kopii. Obecny
fixture usuwa katalog po zakończeniu. W stałym podglądzie operator musi
ustalić retencję i sprzątanie skrzynki. Nie wpisywać prawdziwych adresów.

## Przed rzeczywistą pocztą

Nadal potrzebne są transport TLS/SMTP, kolejka i ponowienia, prawidłowy
nadawca i DNS, weryfikacja adresów oraz odbiór dostarczeń. Demo generuje
niezwiązany token również dla nieznanego konta, aby prywatna skrzynka nie
ujawniała rejestracji. Tego zachowania nie wolno przenieść wprost do SMTP:
rzeczywista wysyłka powinna być ograniczona do uprawnionego odbiorcy, przy
zachowaniu ogólnej odpowiedzi HTTP. Ten pakiet nie włącza takiej wysyłki.
