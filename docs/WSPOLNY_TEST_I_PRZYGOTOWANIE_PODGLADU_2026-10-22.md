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
