# Reklamy przy wejściu do portfela

Zmiana opiera się na PR #62 (23fd019). Nie uruchamia płatności ani nie zmienia prowizji, PIN-u, zamówień, wypłat i rozliczeń w groszach. Nie wykonano wdrożenia na VPS ani na bazie produkcyjnej. Portfel nadal ma dotychczasowe ograniczenia środowiska testowego; ta funkcja nie nadaje aplikacji gotowości produkcyjnej.

## Obsługa

Administrator ma zakładkę **Reklamy portfela**. Formularz umożliwia dodanie nazwy reklamodawcy, zdjęcia JPEG/PNG/WebP do 1 MB, adresu HTTP(S), dat ze strefą czasową, kolejności i przełącznika emisji. Daty w panelu są w lokalnym czasie przeglądarki, API zapisuje czas UTC z dokładnością do pełnych sekund (ułamki są odrzucane zamiast niejawnego zaokrąglania). Edycja może zachować poprzednie zdjęcie. Usunięcie jest logiczne: zatrzymuje przyszłe emisje, zachowuje statystyki w bazie. Lista ma stronicowanie po 10 reklam. Zdjęcie jest ponownie kodowane do JPEG, maksymalnie 500 KB / 2048 px; metadane, w tym GPS, nie są zachowywane. SVG, animacje i uszkodzone pliki są odrzucane.

Aktywne reklamy są uporządkowane po `sort_order,id`; każde konto przechodzi tę listę cyklicznie. Pierwsza emisja zaczyna się od pierwszej aktywnej pozycji. Zmiana harmonogramu lub usunięcie reklamy nie przerywa już wydanej emisji. Przy braku aktywnych reklam limit nie jest zużywany.

Kliknięcie **Portfel** przez klienta lub sprzedawcę sprawdza emisję na serwerze. Modal oznaczony „Reklama” blokuje interakcję z tłem i Escape. X jest nieaktywny przez pięć sekund, licznik pokazuje 5–1, a portfel otwiera się automatycznie bez kolejnego kliknięcia. Odliczanie używa zegara monotonicznego. Reklama nie uruchamia się przy odświeżaniu salda, logowaniu ani zakończeniu operacji finansowej. Konta techniczne nie otrzymują reklam. Przerwane połączenie, brak obsługi UUID lub błąd API otwiera portfel; oczekiwanie na odpowiedź jest ograniczone do dwóch sekund. Wylogowanie i zmiana konta usuwają modal, przerywają żądanie i unieważniają jego wynik.

## API i dane

Wszystkie sześć tras wymaga aktywnej sesji. Operacje, również odczyt administracyjny, ponownie uwierzytelniają konto w tej samej transakcji.

| Metoda i trasa | Uprawnienia | Działanie |
| --- | --- | --- |
| POST `/wallet/ads/claim` | klient, sprzedawca | `{request_key}`; zwraca `{ad:null}` albo bezpieczny baner i losowy identyfikator emisji |
| POST `/wallet/ads/impressions/{id}/click` | właściciel emisji, klient/sprzedawca | idempotentne naliczenie jednego kliknięcia |
| GET `/admin/wallet-ads?limit=10&offset=0` | administrator | kampanie i zagregowane statystyki; limit najwyżej 20 |
| POST `/admin/wallet-ads` | administrator | dodanie kampanii ze zdjęciem base64 |
| PUT `/admin/wallet-ads/{id}` | administrator | edycja; pominięcie zdjęcia zachowuje stare |
| DELETE `/admin/wallet-ads/{id}` | administrator | wyłączenie i logiczne usunięcie |

Limit jest wspólny dla konta, niezależny od sesji, przeglądarki i urządzenia. PostgreSQL blokuje rekord `wallet_ad_accounts` przez `INSERT ON CONFLICT` i `SELECT FOR UPDATE`; SQLite używa istniejącej transakcji `BEGIN IMMEDIATE`. Czas pochodzi z bazy, bez parametrów zegara z klienta. Zapis czasu jest zaokrąglony konserwatywnie: kolejna emisja może być dostępna do sekundy później niż po 30 minutach, nigdy wcześniej. Emisja oraz aktualizacja limitu zatwierdzają się razem. Unikalne `(user_id,request_key)` blokuje ponowne naliczenie wejścia także po upływie limitu. Powtórzone żądanie nie odtwarza reklamy. Kliknięcie zmienia wyłącznie flagę 0→1 w istniejącej własnej emisji.

Statystyka **Emisje** oznacza wydane przez serwer banery, nie potwierdzenie obejrzenia całych pięciu sekund. Zerwanie połączenia po zatwierdzeniu transakcji może zużyć limit bez pokazania banera; jest to celowe zabezpieczenie przed duplikatami. Kliknięcia są unikalne na emisję, nie liczą każdego ponownego naciśnięcia. Usunięte kampanie pozostają w bazie do kontrolowanej retencji; nie występują na bieżącej liście panelu.

Baner jest dostarczany jako oczyszczony JPEG w tej samej odpowiedzi API. Nie ma pikseli śledzących, zewnętrznych bibliotek, żądań do serwera reklamodawcy przy emisji ani przekazywania danych konta reklamodawcom. Zewnętrzny link otwiera się wyłącznie po kliknięciu, z `noopener noreferrer sponsored` i `no-referrer`. Adres nie może zawierać danych logowania, znaków sterujących, backslashy ani niebezpiecznych schematów. Serwer nie pobiera adresu reklamy. Nazwy są renderowane przez `textContent`, nigdy jako HTML. CSP pozostaje bez zmian.

## PostgreSQL / RLS

Tabele `wallet_ads`, `wallet_ad_accounts`, `wallet_ad_impressions` są odrębne od portfela. `002_wallet_ads.up.sql` rozszerza zweryfikowaną funkcję polityk z PR #62 i wymusza RLS dla nowych tabel. Zapis kampanii jest dostępny administratorowi; konta klienta i sprzedawcy widzą tylko własne rekordy limitu i emisji. Kurier nie otrzymuje tych wyjątków. Zachowane są kontrolowane operacje maintenance i odczyty kopii zapasowej z PR #62. Fizyczne konto aplikacji nie dostaje bezpośredniego DML ani własności tabel. Podpisane zapytania pozostają związane z połączeniem, transakcją, dokładnym SQL i aktywną sesją; zmiana `actor_id`/roli w GUC nie zmienia tożsamości.

Historyczna migracja `001` nie została zmieniona. Testowa deklaracja schematu zawiera nowe tabele i zaktualizowany checksum lock, a procedura provision testowego RLS uruchamia następnie `002`. Nie jest to migracja wykonywana automatycznie podczas uruchamiania PostgreSQL przez aplikację.

## Procedura wdrożenia — do wykonania dopiero po zatwierdzeniu wyników i przeglądzie

1. Przeprowadzić lokalne testy funkcji i pełną bramkę RLS z tej gałęzi oraz pełną regresję. Zachować wyniki wraz z SHA kodu. Nie traktować samej flagi SQL jako dowodu zgodności.
2. Wykonać kopię zapasową i próbę odtworzenia zgodnie z procedurą PR #62. Spisać rzeczywiste role, właścicieli, ACL, polityki i ustawienia RLS. Przejrzeć rozszerzenie funkcji `wp_rls.allowed`: migracja jest przeznaczona dla wersji PR #62, nie dla nieznanych lokalnych modyfikacji polityk.
3. Na odizolowanej kopii istniejącej bazy zatrzymać API i workerów. Zastosować `database/security_rls/002_wallet_ads.up.sql` kontem migracyjnym, w sesji ustawiając `SET wp_rls.api_compatibility_verified='yes'` **wyłącznie po uzyskaniu wyników testów**. Skrypt jest transakcyjny i odrzuca brak tej deklaracji; wyjątek dotyczy wyłącznie oznaczonej bazy `wp_test_*`.
4. Dla nowej bazy użyć sprawdzonego manifestu schematu, następnie instrukcji `001` z PR #62 i migracji `002`. Nie uruchamiać samego `optional_wallet_ads.sql` na bazie już chronionej RLS: to deklaracja tabel do budowy testowego schematu, bez polityk dla działającej bazy.
5. Sprawdzić ENABLE i FORCE RLS na wszystkich trzech tabelach, pięć polityk na każdej, brak własności / SUPERUSER / BYPASSRLS / bezpośrednich ACL konta aplikacji i brak uprawnień z default privileges właściciela migracji. Nie przyznawać aplikacji konta migracyjnego ani członkostwa w rolach prywatnych.
6. Uruchomić API z dotychczasowym plikiem klucza gateway, pod ograniczoną rolą; wykonać testy klientów, sprzedawców, administratora i anonimowego użytkownika na kopii. Kampanie początkowo nie istnieją, więc portfel działa bez reklamy. W razie błędów reklam portfel otwiera się bez emisji.
7. Dopiero po przeglądzie osobno zaplanować rzeczywiste wdrożenie. Niniejsza praca nie obejmuje wykonania tych kroków na VPS/produkcji ani nie znosi wcześniejszych blokad gotowości produkcyjnej.

## Wycofanie

Preferowane wycofanie bez utraty danych: wyłączyć kampanie w panelu i przywrócić poprzednią wersję aplikacji; pozostawić nowe tabele i polityki do przeglądu. Portfel zachowuje wcześniejsze działanie.

Pełne wycofanie schematu: zatrzymać API i workerów, zarchiwizować tabele reklam i zagregowane statystyki, wycofać kod funkcji, uruchomić `002_wallet_ads.down.sql` kontem migracyjnym. Skrypt przywraca funkcję polityk PR #62 i usuwa wyłącznie trzy tabele reklam oraz ich wpisy rejestru rollbacku. **Usuwa dane reklam**; późniejsze `up` nie odtworzy statystyk bez kopii. Nie wycofywać `001` jako sposobu wyłączenia reklam. Nie przyznawać szerszych uprawnień aplikacji. Zweryfikować saldo, historię portfela, logowanie i izolację kont. Test automatyczny wykonuje cykl down/up i porównuje nienaruszone rekordy finansowe.

## Testy i pozostałe ograniczenia

Polecenia (lokalnie, bez danych produkcyjnych):

```sh
python -m pytest -q tests/test_wallet_ads_http.py tests/test_wallet_ads_browser.py
python -m scripts.run_rls_api_gate --report work/wallet-ads-rls.xml --coverage work/wallet-ads-rls-routes.jsonl
python scripts/run_full_regression.py --shard 1/2 --timeout 360 --report work/wallet-ads-full-1.json
python scripts/run_full_regression.py --shard 2/2 --timeout 360 --report work/wallet-ads-full-2.json
```

Wyniki końcowe należy odczytać z raportu w Pull Request i raportu końcowego tej gałęzi. Testy RLS tworzą i usuwają wyłącznie własny lokalny PostgreSQL. Testy obejmują równoczesne żądania, izolację i spoofing GUC, zabronione zapisy, migrację i rollback, harmonogram, wylogowanie/restart, kliknięcia, XSS, walidację zdjęć/linków i rzeczywisty Chromium na telefonie/komputerze.

Pozostałe ograniczenia: złośliwa przeglądarka może ominąć prezentację reklamy, ponieważ reklama nie jest warunkiem autoryzacji finansowej. Wyłączone lub zawieszone karty mogą opóźnić timer do wznowienia wykonywania JS. Docelowa strona po dobrowolnym kliknięciu otrzymuje standardowe dane własnego połączenia sieciowego, ale nie dane konta WiejskaPaka ani referrer. Zewnętrzne adresy i treści wymagają nadzoru administratora; aplikacja nie ocenia wiarygodności reklamowanej strony. Retencja historycznych emisji wymaga przyszłej decyzji operacyjnej i nie jest realizowana przez automatyczne kasowanie danych w tej zmianie.
