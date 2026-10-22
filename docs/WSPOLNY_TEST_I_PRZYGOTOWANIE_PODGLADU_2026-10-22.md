# Wspólny test nowych modułów i przygotowanie podglądu

Ten etap dotyczy zamkniętego środowiska testowego. Nie wykonano zmian na VPS ani w konfiguracji domeny, poczty lub operatora płatności.

## Zakres wspólnego scenariusza

`tests/test_combined_marketplace_http.py` uruchamia rzeczywisty serwer HTTP na jednorazowej bazie SQLite z jednocześnie włączonymi jednostkami sprzedaży, zdjęciami użytkowników, publicznymi loginami sprzedawców oraz dostawami na adres.

Scenariusze obejmują:

- znalezienie gospodarstwa po publicznym loginie bez ujawniania prywatnego e-maila;
- katalog produktów tego sprzedawcy, kg i słoik z zawartością 0,75 l;
- zapis zdjęcia jako JPEG do 1 000 000 bajtów, usunięcie metadanych i odrzucenie zapisu przez obcą osobę;
- dwie pozycje we wspólnej paczce: 2 × 349 gr + 299 gr + jedna dostawa 501 gr = 1498 gr;
- ponowienie checkout z tym samym kluczem bez utworzenia drugiej przesyłki;
- ukrycie numeru telefonu w widokach klienta i sprzedawcy;
- rzeczywisty restart procesu i odczyt zachowanych zdjęć, jednostek oraz warunków zakupu;
- wspólną akceptację albo odrzucenie obu pozycji, idempotentne ponowienie decyzji i jednokrotne przywrócenie magazynu po odrzuceniu;
- brak dostępu obcego klienta do zapisów zakupu.

## Przygotowanie konfiguracji

Szablon `deploy/preview/preview.env.example` jawnie wymienia cztery flagi; wszystkie mają wartość `0`. Ich włączenie wymaga odpowiednich migracji w testowej bazie PostgreSQL:

| Flaga | Migracja |
| --- | --- |
| `WP_ENABLE_PRODUCT_UNITS` | `database/optional_product_sale_units.sql` |
| `WP_ENABLE_ADDRESS_DELIVERY` | `database/optional_address_delivery.sql` |
| `WP_ENABLE_USER_PHOTOS` | `database/optional_user_photos.sql` |
| `WP_ENABLE_SELLER_SEARCH` | `database/optional_seller_directory.sql` |

Wszystkie migracje są już ujęte w szablonie przygotowania **nowej** testowej bazy `deploy/preview/new-test-database.psql.example`. Ten skrypt nie służy do odtwarzania ani nadpisywania istniejącej bazy. Istniejący podgląd wymaga osobnego sprawdzenia obecnego schematu, kopii bazy i klucza sejfu oraz zastosowania brakujących migracji przez administratora. Nie należy zastępować istniejącego pliku środowiska szablonem zawierającym wartości przykładowe.

Zamknięty test zakupów korzysta z `WP_ENABLE_TEST_PAYMENTS=1`, przy `WP_REAL_PAYMENTS=0` i `WP_ENV=test`. Ustawienie to służy operacjom symulowanym; nie uruchamia PayU ani innego rzeczywistego operatora. Konfiguracja i klucze pozostają poza repozytorium.

## Granice wyniku

Ten wspólny scenariusz jest testem HTTP i trwałości na SQLite. Osobne testy PostgreSQL i przeglądarki nie zastępują późniejszej weryfikacji jednocześnie włączonych funkcji na docelowym VPS. Trzeba tam sprawdzić również uprawnienia roli aplikacji, migracje, certyfikat HTTPS, kopię i odtworzenie danych oraz widoki telefonu i komputera.

Rzeczywiste płatności i SES pozostają odrębnym etapem integracji. Zakupy ułamkowe, np. 0,5 kg, nie są częścią tego scenariusza ani istniejącego checkout pełnych jednostek.

## Weryfikacja lokalna

22.10.2026: `python -m pytest tests/test_combined_marketplace_http.py -q` — 2 PASS, 0 FAIL, rzeczywisty HTTP i dwa restarty procesu (po jednym dla każdej decyzji). Kontrola `git diff --check` — PASS. Wynik dotyczy obu scenariuszy ze wszystkimi czterema flagami ustawionymi na `1`.

## CI i stabilność wykonania

Przebieg `39790000841` dla `d9d6df480a1e4f8eb677f1c6181807a36d47a886`: Chromium 48/48 oraz HTTP na pięciu rozmiarach ekranu PASS, PostgreSQL 16 i 17 po 53/53 PASS, szybki Windows 80/80 PASS. Pełny Windows nie został zaliczony: dwa moduły (`test_b901_reconciliation.py`, `test_b91_b95_http_boundaries.py`) przekroczyły dotychczasowe 90 sekund, a test zwykłego uruchomienia procesu pocztowego `test_bounded_reset_worker.py` nie spełnił oczekiwanego wyniku w budżecie 10 sekund. Raporty zachowano w `docs/audits/combined_features_2026-10-22/native_d9d6df4/`.

Limit pojedynczego modułu w pełnym Windows zwiększono do 180 sekund. Budżet zwykłego testu wysłania dwóch syntetycznych wiadomości przez proces potomny wynosi 30 sekund. Testy wymuszonego zawieszenia nadal mają limity 1 i 3 sekund i nadal sprawdzają niepewny wynik oraz brak ponownej wysyłki. Nie zmieniono produkcyjnego mechanizmu dostarczania wiadomości.

Lokalny izolowany przebieg obejmujący trzy wskazane moduły, wspólny test czterech funkcji oraz runner CI: 68 PASS, 0 FAIL, 0 SKIP, 5/5 modułów, źródła niezmienione podczas testów. Dowód: `docs/audits/combined_features_2026-10-22/local_stability_summary.json`. Wymagany jest ponowny pełny Windows; ostatnia zaliczona pełna regresja wersji bazowej pozostaje odrębnym wynikiem.

## Pełny Windows po korekcie budżetów — 22.10.2026

Przebieg `39794532814` dla commitu `f7a7082a74b0a47c38219d1631efb6ffd4eb5cd3`: pełna izolowana regresja Windows zakończona powodzeniem, 4369 testów łącznie — 4196 PASS, 0 FAIL, 173 SKIP. Brak timeoutów, niekompletnych i błędnych modułów; źródła niezmienione podczas przebiegu. Szybki Windows 80/80, Chromium 48/48 z HTTP na pięciu rozmiarach ekranu i PostgreSQL 16 53/53 również PASS. Raporty: `docs/audits/combined_features_2026-10-22/native_f7a7082/`.

PostgreSQL 17 został przerwany przed testami na etapie instalacji klientów kopii zapasowej. Po zakończeniu Windowsa ponowiono wyłącznie to zadanie bez zmian kodu. Jego wynik jest oddzielny od zaliczonej pełnej regresji Windows.
