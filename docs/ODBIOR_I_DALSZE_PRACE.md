# Odbiór wersji testowej i następne prace

Stan uzupełniony 18 października 2026. To lista warunków odbioru, nie zgoda
na produkcyjne integracje. Wyniki natywnych testów wraz z zakresem i badanym
commitem znajdują się w `RAPORT_DEMO_I_ROZLICZEN_2026-10-18.md` oraz raporcie
kolejnego pakietu `RAPORT_PANELU_FINANSOWEGO_2026-10-18.md`.
Narzędzie lokalnej kopii i odtworzenia opisuje `ODTWARZANIE_SQLITE.md`.

| Obszar | Obecny stan | Warunek dalszego odbioru |
| --- | --- | --- |
| PostgreSQL | Adapter, migracje i natywna bramka CI zaliczona dla commitu wskazanego w raporcie | Jednorazowy lokalny serwer pod nieuprzywilejowaną tożsamością, izolowana baza, ograniczona rola aplikacji; pełny zestaw natywny bez SKIP, w tym sesje, wyścigi, zakup i zwrot |
| Chromium i telefon | Natywne Chromium i testy viewportów zaliczone w CI dla commitu wskazanego w raporcie | Uruchomienie rzeczywistej przeglądarki; odbiór każdej roli na wąskim ekranie, klawiaturą, z utratą sieci i przełączeniem konta |
| Zapomniane hasło | Zmiana hasła wymaga starego; lokalny reset demo ma jednorazowe tokeny i prywatną skrzynkę, bez rzeczywistej wysyłki | Zatwierdzony kanał kontaktu, krótkotrwały losowy token trzymany w postaci skrótu, jednorazowe użycie, limit prób, ochrona przed ujawnianiem istnienia konta i cofnięcie sesji po zmianie; brak resetu samym e-mailem lub ID |
| Utrata PIN-u | Odzyskanie istniejącego kodu po haśle do 24 godzin; bez resetu blokady | Bezpieczny kanał produkcyjny i procedura po upływie retencji, bez drugiego zakupu i bez obchodzenia licznika prób odbioru |
| Weryfikacja sprzedawcy | Testowe potwierdzenie zasad i przegląd administracyjny; bez danych identyfikacyjnych i prawdziwych wypłat | Ustalony cel i podstawa przetwarzania, bezpieczny operator, minimalny zakres, retencja i kontrola dostępu; bez wpisywania prawdziwych danych do demo |
| Próg uzupełnienia profilu | Przypomnienie po 20 odebranych transakcjach; przesyłka wieloproduktowa liczona raz; potwierdzenie zasad w UI (PROFIL_ROLNIKA_TESTOWY.md) | Reguła produktu oddzielona od progów prawnych; docelową weryfikację ustalić osobno |
| Płatności i wypłaty | Wyłącznie symulacje; grosze, idempotencja, pełny zwrot i historia | Uzgodniony operator i model opłat, weryfikacja zdarzeń i uzgodnienie sald; integracji produkcyjnej nie uruchamiać w obecnym zadaniu |
| Dostawcy i punkty | Opłata za adres naliczana raz w przesyłce; odbiór w punkcie | Uzgodnić wynagrodzenia i odpowiedzialność stron; nie wyprowadzać ich z samej testowej funkcji podziału 75/20/5 |
| Prawa konsumenta | Informacja o zachowaniu ustawowych praw; PIN potwierdza odbiór | Niezależna ocena docelowych regulaminów, informacji i procesów obsługi; nie utożsamiać testowego anulowania z kompletną procedurą konsumencką |
| Dane i kopie | Szyfrowany cache PIN; lokalna kopia i izolowane odtworzenie SQLite z cofnięciem sesji; osobne narzędzie szyfrowanej kopii z niezależnym kluczem i limitem 64 MiB | Docelowa ochrona całej bazy, kluczy, kopii i logów; odtworzenie oraz usuwanie danych zgodnie z przyjętą retencją |

## Co można teraz sprawdzić lokalnie

Uruchomić jednorazowe demo z czterema rolami według `DEMO_Z_DANYMI.md`,
tworzyć wyłącznie syntetyczne konta,
produkty i zakupy. Potwierdzić dodatnią opłatę przy dostawie na adres, odbiór
w punkcie, jedną opłatę za przesyłkę, sprawdzenie towaru przed PIN-em, blokadę
kodu po błędnych próbach oraz testowy pełny zwrot z dostawą przy winie dostawcy.

W panelu konta sprawdzić liczbę sesji po dwóch logowaniach, wylogować pozostałe,
sprawdzić odrzucenie starego tokenu i zachowanie bieżącego. Następnie zmienić
hasło i potwierdzić odrzucenie wszystkich wcześniejszych tokenów. Zmiana hasła
nie powinna zmieniać zamówień, klucza szyfrowania ani budżetu odzyskiwania PIN-u.

Powtórzone uruchomienia należy liczyć oddzielnie od odrębnych przypadków testów.
Nie nadawać statusu PASS zadaniu, które nie zostało uruchomione, nie uznawać
kontroli źródeł za wykonanie w przeglądarce i nie przenosić wyników SQLite na
PostgreSQL. Wynik testu śmierci procesu nie jest certyfikatem odporności na
awarię dysku lub utratę zasilania.

## Ograniczenia pracy autonomicznej

Dalsze poprawki rozwijać na `wiejskapaka-import`; nie zmieniać bezpośrednio `main`.
GitHub i izolowane CI są dopuszczone zgodnie z późniejszym poleceniem użytkownika.
Nie korzystać z usług płatnych ani połączeń produkcyjnych.
Nie podłączać Neon, płatności, domeny ani hostingu. Na gałąź roboczą publikować wyłącznie kod i oczyszczone dowody; nie publikować
danych, baz ani kluczy. W ZIP przekazywać kod, testy i dowody; robocze dane oraz klucz
pozostawić poza archiwum. Nie zbierać ani nie udostępniać telefonów użytkowników.

## Zamknięty podgląd przed wdrożeniem

`ZAMKNIETY_PODGLAD_SSH.md` opisuje przygotowany lokalnie podgląd przez SSH
z prywatnym plikiem kont zamiast haseł w logach. To jednorazowe demo SQLite,
nie trwała instalacja PostgreSQL ani wynik pomiaru docelowego serwera.

Kontrolę konfiguracji i rdzenia PostgreSQL przed startem opisuje
`PREFLIGHT_POSTGRESQL_PODGLAD.md`. Nie tworzy ani nie migruje bazy, a jej
sukces nie zastępuje testu trwałości, kopii i rzeczywistego wdrożenia.

## Zamknięty pakiet testowania — 18.10.2026

`WYNIK_KONCOWY_TESTOW_BEZ_HOSTINGU_2026-10-18.md` zapisuje komplet wyników
dla commitu e83feaf: pełny Windows i Linux, natywny PostgreSQL i Chromium,
akceptację HTTP i stabilność lokalną. Wszystkie bramki zakończone sukcesem.
To nie odbiór hostingu, rzeczywistych płatności ani brakujących funkcji.

Dodatkowy pakiet trwałości po restarcie API PostgreSQL również zakończono:
`RESTART_APLIKACJI_POSTGRESQL_2026-10-18.md` (kod 9f5fe15). PostgreSQL 21/21,
Chromium 36/36 oraz pełny Linux i Windows zaliczone; odrębnie pokazano
pominięcia i zakres dowodu. Hosting oraz prawdziwe płatności pozostają poza
wykonanym zakresem.


## Pakiet uruchomienia i kopii PostgreSQL

`RAPORT_KOPII_POSTGRESQL_2026-10-18.md` wskazuje badany kod i aktualne
wyniki. Natywna próba pg_dump/pg_restore 16, pełny Linux i pełny Windows
zakończone sukcesem; raport rozdziela zaliczenia i pominięcia.
`URUCHOMIENIE_PODGLADU_NA_SERWERZE.md` zawiera szablony na zakupiony VPS.
Żadnej usługi jeszcze nie zainstalowano na docelowym serwerze.

`POCZTA_STAN_KODU_I_ODBIOR.md` rozdziela zakup skrzynki od brakującej
integracji: zamknięty reset na PostgreSQL używa skrzynki plikowej, a adapter
SMTP wymaga jeszcze połączenia z kolejką i zweryfikowanym odbiorcą.
Podgląd ze sztucznymi danymi i rzeczywista sprzedaż mają różne warunki
odbioru; zakup infrastruktury sam ich nie zamyka.


## Reset PostgreSQL i przygotowanie SMTP

`RAPORT_POCZTY_PRZYGOTOWANIE_2026-10-18.md` opisuje pakiet kodu 6fe0712.
Reset na dedykowanej lokalnej bazie PostgreSQL wymaga jawnego opt-in;
serializuje równoległe żądania i cofa sesje w tej samej transakcji.
Adapter SMTP jest osobnym, domyślnie wyłączonym modułem, sprawdzanym
wyłącznie z obiektem w pamięci. Nie uruchamia wysyłki z aplikacji.
Raport podaje stan bramek oraz dalszy zakres kolejki i weryfikacji adresów.


## Odłączona kolejka resetu SQLite — 19.10.2026

`RAPORT_KOLEJKI_POCZTY_2026-10-19.md` dokumentuje kod 47bbfe3.
Szyfrowane zadanie, dzierżawy i pojedyncze wykonanie są zaimplementowane
w osobnym module SQLite. Nie ma integracji HTTP ani domyślnego transportu.
Nadal wymagane są PostgreSQL, zarządzanie kluczami, retencja, właściwy
pracownik i potwierdzanie adresów. Nowy moduł nie uruchamia poczty aplikacji.


## Wykonywanie PostgreSQL i prywatne klucze — kolejny pakiet 19.10.2026

`RAPORT_KOLEJKI_POSTGRESQL_I_KLUCZY_2026-10-19.md` dotyczy kodu 60526b0.
Wykonywanie na PgConnection, transakcje i blokady wierszy oraz jawny odczyt
prywatnych wersjonowanych kluczy są objęte oddzielnym odbiorem. Nie uruchamiają
poczty z aplikacji. Pozostają integracja HTTP, pracownik, retencja, kopie
kluczy, potwierdzenie adresów i odbiór rzeczywistych dostarczeń.
