# Portfel konta — trwały podgląd przed integracją operatora

Nowy moduł WP_ENABLE_WALLET_PREVIEW=1 zapisuje portfel zalogowanego klienta lub sprzedawcy w bazie. Domyślnie wyłączony; dozwolony wyłącznie WP_ENV=test/testing/development. Nie jest księgowością rzeczywistych środków i nie autoryzuje zapłaty za zamówienie ani przelewu do banku. Doładowanie w tym prywatnym trybie jest ręcznym zasymulowaniem uznania. Przed wdrożeniem publicznym zastąpić je potwierdzonym zdarzeniem operatora płatności; nie używać tej trasy jako prawdziwego doładowania.

## Widok

Portfel jest dostępny z nawigacji po zalogowaniu, gdy funkcja działa. Dostępne saldo, rezerwa i ostatnie 50 operacji pochodzą z serwera. Doładowanie nie wymaga PIN-u. Wypłata wymaga osobnego sześciocyfrowego PIN-u portfela; jego ustawienie i zmiana wymagają hasła konta. W samym portfelu nie ma etykiet środków testowych, zgodnie z życzeniem użytkownika. Istniejące oznaczenie środowiska na stronie pozostaje.

Rezerwa obejmuje w tej wersji oczekujące wypłaty. Wypłata jedynie przenosi saldo do rezerwy i tworzy wpis pending; nie wykonuje przelewu. Brakuje powiązania z rachunkiem bankowym, operatora realizującego wypłatę, końcowego rozliczenia/odrzucenia wypłaty, zakupów i zwrotów oraz uznawania przychodów sprzedawcy. Tych działań nie należy prezentować jako zakończonych.

## Integralność

Kwoty są ścisłymi liczbami całkowitymi groszy. Limit pojedynczej operacji 1 000 000 zł, łącznego salda 10 000 000 zł. Saldo, rezerwa i niepowtarzalny wpis operacji są zapisywane w jednej autoryzowanej transakcji. Konto portfela jest blokowane FOR UPDATE w PostgreSQL; SQLite korzysta z istniejącego BEGIN IMMEDIATE. Numer rewizji porządkuje historię, również dla zdarzeń w tej samej sekundzie. Ujemne stany i niespójne rodzaje/statusy są odrzucane przez constraints.

Idempotencyjny request_key jest unikatowy w obrębie właściciela; inna kwota/rodzaj z tym samym kluczem daje 409. Przeglądarka zachowuje tylko identyfikator i kwotę nierozstrzygniętej operacji w sessionStorage per konto i rodzaj. Nie przechowuje tam salda, PIN-u, hasła ani tokenu logowania. Ponowienia wypłaty nadal wymagają poprawnego PIN-u. PIN jest haszowany Argon2; po pięciu błędnych próbach PIN-u/hasła portfela blokada trwa 15 minut i przeżywa restart. Błędne próby są zatwierdzane w bazie przed odpowiedzią błędu. Wylogowanie czyści widok i pola haseł/PIN-ów, a odpowiedź ze starej sesji nie zmienia kolejnego konta.

## Wdrożenie

Migracja optional_wallet_preview.sql tworzy dwie nowe tabele. Jawne uprawnienia roli aplikacji: SELECT,INSERT,UPDATE na wallet_preview_accounts oraz SELECT,INSERT na wallet_preview_entries. Brak migracji automatycznych PostgreSQL, brak zmiany istniejących danych lub płatności. W preflight włączyć WP_ENABLE_WALLET_PREVIEW=1 i zachować aktualne flagi e-maila, zdjęć, kalendarza oraz jednostek. Dopiero potem zmienić wydanie głównej aplikacji i uruchomić funkcję. Nie zmieniać odbiornika SNS ani workerów SMTP.

## Weryfikacja

Przed zmianą końcowego dodatkowego constraintu 71 lokalnych testów API, manifestu, preflightu, audytu uwierzytelniania i UI przeszło. Scenariusze: trwałość po restarcie, ponowienia, konflikty kluczy, izolacja kont, brak dostępu bez sesji i dla dostawcy, błędny PIN/hasło, trwała blokada, poprawne rezerwowanie środków, równoległe wypłaty bez podwójnego wydania oraz rollback salda przy błędzie dziennika. Dwa natywne testy PostgreSQL i testy Chromium 320/1280 dodano do CI; lokalnie nie uruchomiono PostgreSQL/Chromium. Bieżący wynik CI wymaga sprawdzenia.

Po dodaniu końcowego constraintu 62 testy API, manifestu, preflightu i UI ponownie przeszły. Składnia JavaScript sprawdzona. Testy rzeczywistej przeglądarki i PostgreSQL pozostają do wykonania w CI przed wdrożeniem.
