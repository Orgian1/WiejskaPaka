# Ostatnie poprawki WiejskaPaka — 12.11.2026

Nie jest to pełny odbiór wszystkich wymagań. Pozostają wybór lokalizacji
sprzedawcy na mapie oraz administracyjny kod promocyjny na trzy darmowe punkty.
Nie publikowano środowiska, nie zmieniano main, VPS, produkcyjnych danych ani
sekretów. Wszystkie płatności i zwroty w testach były lokalnymi symulacjami.

## Kod i bezpieczeństwo pracy

- Źródło: `codex/demo-finalization-20261112`, commit
  `473c75514fa4816a2d61a05c8983742f1497404a` pobrany z origin.
- Osobna lokalna gałąź zmian: `codex/demo-finalization-fixes-20261112`.
- Implementacja i testy: `878e86d5d10e0bde1b63aa76414ef8f741f0691d`.
- Końcowa poprawka widoczności zakładki Ulubione dla ról: `01b1aee7c46e1bfc25a1ce9b1f32947965a6ace9` (8 nowych zaliczeń po tej poprawce).
- Początkowy katalog roboczy był czysty. Nie używano reset --hard, nie
  nadpisywano lokalnych zmian, nie wysyłano commitów do origin.
- Python 3.12 i zależności z niezmienionego `requirements-lock.txt`, osobny venv.
  PostgreSQL 17.11 uruchomiony jako bieżący użytkownik wyłącznie lokalnie.
  Pakiety pobrano przez APT z weryfikacją podpisanego indeksu Debiana.

## Zakres wymagań właściciela

| Nr | Wynik tej partii |
| --- | --- |
| 1 | Udana płatność testowa odbioru ustawia `gotowe_do_odbioru_testowo` w tej samej transakcji; nie jest potrzebna akcja sprzedawcy. Powtórzenie tego samego zdarzenia nie powiela zmiany. Zachowano istniejącą rezerwację, blokady magazynu i akceptację dostawy na adres. |
| 2 | Odbiór pojedynczego zamówienia i przesyłki samym PIN-em, bez checkboxa w panelu sprzedawcy i dostawcy. Stare jawne `checked_goods` pozostaje zgodne z wcześniejszym API; nowe formularze go nie wysyłają. Zachowano limit prób, uprawnienia i jednorazowość. |
| 3 | **NIEUKOŃCZONE:** istniejące wyszukiwanie adresów klienta zachowano, ale nie dodano mapy wyboru punktu sprzedawcy. Zewnętrzny geokoder nadal wymaga istniejącej, jawnej konfiguracji operatora. |
| 4 | Dobrowolny zapis lokalizacji na koncie, odczyt przy ponownym logowaniu i wyszukanie pobliskich ofert, zmiana przez adres/GPS i usuwanie zapisu. Współrzędne pozostają poza URL i pamięcią przeglądarki. Dane oddzielone per konto. Zachowano komunikaty odmowy GPS; nowe testy wykonują ścieżkę udzielonej zgody. |
| 5 | Trwałe ulubione per konto, osobna zakładka obok „Blisko mnie”, idempotentne dodawanie/usuwanie i odtwarzanie po restarcie. |
| 6 | **NIEUKOŃCZONE:** brak administracyjnej konfiguracji kodu, terminu i limitu użyć. Dotychczasowe demo nie nalicza opłat za tworzenie punktów; nie wprowadzano domyślnego cennika ani pozornych płatności. |
| 7 | Zachowano jedną opłatę za przesyłkę i pełne zwroty po nieudanej dostawie. Anulowanie opłaconego odbioru działa także po automatycznym ustawieniu gotowości, z kontrolą historii i bez podwójnego zwrotu. |
| 8 | Zachowano jeden portfel na konto, integer/grosze, prowizję 5% dla sprzedawcy i 0% dla klienta, niezmienne warunki wypłat oraz blokady operacji. SQLite i natywny PostgreSQL sprawdzają te przepływy. |
| 9 | Nowe odpowiedzi nie dodają telefonów ani profili klientów. Grupowanie korzysta wyłącznie z zamówień autoryzowanego sprzedawcy. Informacje o prawach konsumenta zachowane. |
| 10 | Istniejące migracje `optional_wallet_withdrawals.sql` i `optional_wallet_operation_fences.sql` zawierają wszystkie trzy wskazane tabele. Zastosowano je lokalnie i wykonano testy portfela z ograniczoną rolą PostgreSQL. Nie wykonano żadnej migracji VPS. |
| 11 | Zachowano jednostki, zdjęcia i tryby testowe. Testy zdjęć obejmują upload, odczyt, wymianę, błędny plik, usunięcie i wylogowanie na mobile/desktop. Nie podłączano PayU ani rzeczywistej poczty. Nie wykonano kompletnej regresji wszystkich raportów. |
| 12 | Nie odczytywano świeżych logów VPS. Historycznego 404 nie traktowano jako aktualnej awarii; testy lokalnych zdjęć sprawdzają faktyczne odpowiedzi. |
| 13 | Responsywny katalog w rzędach; natywne `details/summary` rozwijają szczegóły pod produktem bez zmiany strony. Stan rozwinięcia zachowany przy odświeżaniu danych w sesji. |
| 14 | Puste czerwone serce / pełne czerwone serce w prawym dolnym rogu zdjęcia, obszar dotyku 44 px, `aria-pressed`, synchronizacja z ulubionymi. Kliknięcie serca nie rozwija produktu. |
| 15 | Rozwijane grupy aktualnych zamówień według ID punktu: liczba, numery, nazwy produktów, ilości; bez telefonów. Zapytania SQLite i PostgreSQL zachowują zakres konta. |
| 16 | Górne menu „Dodaj punkt”, przyciski zmiany kolejności, linki Google Maps. Długie listy dzielone na etapy mieszczące się w limicie mobilnym trzech punktów pośrednich. Bez wyliczania tras i ETA. Kolejność zapisywana per konto **w danej przeglądarce**, bez synchronizacji między urządzeniami. |
| 17 | Dodatkowe panele sprzedawcy domyślnie zwinięte; aktualne zamówienia i uzupełnianie towaru rozwinięte. Po ponownym logowaniu/przeładowaniu wracają przewidywalne ustawienia domyślne. Link dodawania punktu otwiera profil i ustawia fokus formularza. |
| 18 | Testy interakcji Chromium na szerokościach 320 i 1280 px oraz testy HTTP/SQLite/PostgreSQL. Pełna wielotysięczna regresja projektu, Windows, PostgreSQL 16 i fizyczny telefon nie były wykonywane. |

Formularz Kontakt / Zgłoś problem pozostał publiczny i responsywny, z wyłączoną
wysyłką. Nie dodano zewnętrznych skryptów, nie osłabiono CSP, TLS ani weryfikacji
pakietów.

## Migracja nowych funkcji

Nowy plik `database/optional_account_favorites.sql` tworzy `account_favorites`
i `account_saved_locations`. Dodano go do manifestu, checksumów i przykładu
`deploy/preview/new-test-database.psql.example`; wcześniejsze pliki SQL nie
zostały zmienione. Odczyt gotowości i start aplikacji wykrywają brak nowych tabel.
SQLite przygotowuje je lokalnie. PostgreSQL wymaga jawnej migracji oraz nadania
roli aplikacji SELECT/INSERT/DELETE dla ulubionych i SELECT/INSERT/UPDATE/DELETE
dla zapisanej lokalizacji. Testy używają jednorazowych baz i ograniczonej roli.
Nie uruchamiać przykładu tworzenia nowej bazy na istniejącej produkcyjnej bazie.

## Wyniki

Ostateczne wyniki i lista izolowanych modułów są zapisane w
`docs/audits/demo_finalization_20261112/results.json`.
Zestawy częściowo się pokrywają; nie sumować ich jako unikalnych przypadków.

| Końcowy zestaw | PASS | FAIL | SKIP |
| --- | ---: | ---: | ---: |
| SQLite, 21 modułów uruchomionych osobno | 143 | 0 | 0 |
| Chromium + HTTP/formularz Kontakt/zdjęcia, 6 modułów | 32 | 0 | 0 |
| PostgreSQL 17.11, pełny natywny moduł HTTP | 94 | 0 | 0 |
| Schemat, manifest, checksumy i Kontakt | 15 | 0 | 0 |
| Końcowa widoczność nawigacji: 4 role × 2 szerokości | 8 | 0 | 0 |

Ostatni zestaw miał dodatkowo 2 przypadki **deselected**, a nie SKIP.
Ostateczna zmiana po większych zestawach dotyczy tylko ukrycia zakładki
Ulubione dla administratora i dostawcy; sprawdzono wszystkie cztery role.
Launcher pełnego demo: strona, `/health`, `/products` — HTTP 200; katalog
zawierał 2 produkty. Po przerwaniu launchera prywatny plik kont został usunięty.
Manifest i weryfikacja checksumów: 41 plików SQL, bez rozbieżności.

Wybrane zestawy można powtórzyć następująco (aktywny venv):

```sh
python -m pytest -q tests/test_catalog_page_browser.py tests/test_sample_demo_browser.py tests/test_owner_finalization.py tests/test_favorites_http.py tests/test_footer_contact.py tests/test_user_photos_browser.py
python -m pytest -q tests/test_postgres_full_api_optin.py
python -m database.verify_test_migrations
```

Przed poleceniem PostgreSQL należy ustawić `WP_TEST_POSTGRES_DSN` dla własnego
lokalnego, jednorazowego klastra zgodnie z nagłówkiem modułu. Bez tej zmiennej
testy są pomijane; tutaj zostały rzeczywiście wykonane. Nie stosować DSN VPS.
Każdy z 21 modułów wymienionych w `results.json` uruchamiać oddzielnie:
`python scripts/run_tests_isolated.py -q tests/NAZWA_MODULU.py`.


Wstępne przebiegi ujawniły: klaster PostgreSQL w SQL_ASCII zamiast UTF-8,
konflikt ustawień przy wspólnym uruchomieniu modułów SQLite, brak nowej migracji
w przykładzie psql, stare oczekiwanie checkboxa w teście, oczekiwanie ukrytych
kontrolek po zwinięciu paneli, wariant `wait_for_function` wymagający eval,
rozciąganie serca na całą szerokość przez stary styl mobilny oraz utratę fokusu
przez domyślną nawigację kotwicy. Poprawiono konfigurację, implementację lub
scenariusze odpowiednio do przyczyny. Nie wyłączano zabezpieczeń ani asercji
finansowych. Wyniki historyczne z instrukcji właściciela nie są nowymi wynikami.

## Odbiór lokalnego demo

Z katalogu repozytorium, w aktywnym venv Python 3.12:

```sh
python -m pip install -r requirements-lock.txt
python scripts/run_phone_demo.py --full-demo
```

Launcher tworzy jednorazową SQLite, nowe fikcyjne konta wszystkich ról i produkty.
Dane logowania są w terminalu; nie wpisywać prawdziwych danych. Serwer nasłuchuje
wyłącznie lokalnie, domyślnie na porcie 8765. Ctrl+C kończy demo i usuwa jego bazę.
Nie używać bazy z VPS ani produkcyjnych sekretów.

1. Klient: rozwiń kartę, dodaj serce, sprawdź Ulubione, wyloguj/zaloguj się.
2. Wybierz adres lub udziel zgody GPS, zapamiętaj lokalizację, ponownie zaloguj
   się; następnie usuń zapis. Sprawdź też odmowę GPS ręcznie.
3. Sprzedawca: rozwiń grupę punktu i sprawdź pozycje; potwierdź odbiór samym PIN-em.
4. Rozwiń górne „Dodaj punkt”, zmień kolejność; link nawigacji przekazuje publiczne
   adresy do Google Maps. Kliknięcie uruchamia usługę zewnętrzną dopiero świadomie.
5. Sprawdź zwinięte profile/punkty i rozwinięte aktualne zamówienia/uzupełnianie.
6. Przetestuj portfel wyłącznie jako symulację i zachowany formularz Kontakt.

Nie jest to zgoda na publikację ani wdrożenie. Pozostałe dwa wymagania funkcjonalne
oraz niewykonane pełne zestawy testów trzeba zamknąć przed deklaracją pełnego odbioru.
