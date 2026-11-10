# Kontrola nowych modułów przed startem podglądu

Przed tą zmianą kontrola `scripts/check_postgres_preview.py` sprawdzała tylko główne tabele. Mogła zakończyć się powodzeniem mimo włączonej funkcji bez jej migracji. Teraz kontrola i launcher `backend.test_server_launcher` wymagają także tabel funkcji włączonych przez flagi:

| Flaga ustawiona na `1` | Wymagane tabele |
| --- | --- |
| `WP_ENABLE_PRODUCT_UNITS` | `product_sale_units`, `order_sale_units` |
| `WP_ENABLE_ADDRESS_DELIVERY` | `seller_delivery_windows`, `address_delivery_requests` |
| `WP_ENABLE_USER_PHOTOS` | `user_photos` |
| `WP_ENABLE_SELLER_SEARCH` | `seller_public_logins` |

Wartości flag odpowiadają zachowaniu aplikacji: funkcję włącza dokładnie `1`. Domyślnie wyłączone funkcje nie wymagają swoich tabel.

Brak wymaganej tabeli blokuje uruchomienie serwera przed importem aplikacji i wystawieniem HTTP. Launcher zachowuje ogólny komunikat błędu, bez adresu bazy, hasła lub ścieżki klucza. Dodatkowe nazwy tabel są przekazywane jako parametry istniejącego zapytania odczytującego metadane.

Kontrola CLI nadal używa połączenia PostgreSQL tylko do odczytu, z limitem zapytania 5 sekund i blokady 1 sekundy. Nie wykonuje migracji ani zapisów. Raport dodaje `enabled_optional_features` oraz `database_optional_checked`. Gdy brak włączonych funkcji opcjonalnych, drugie pole pozostaje `false`; sukces kontroli głównego schematu pozostaje możliwy.

Kontrola sprawdza obecność tabel. Nie zastępuje weryfikacji kolumn, ograniczeń, wszystkich uprawnień, kopii i odtworzenia bazy, testów HTTP ani testów na docelowym VPS. Powodzenie nie oznacza gotowości produkcyjnej, uruchomienia podglądu ani aktywacji poczty lub płatności.

## Walidacja lokalna

51 testów kontroli PostgreSQL i kolejności uruchamiania: PASS. Obejmują brak każdej z sześciu tabel przy włączonej funkcji, komplet wszystkich tabel, wyłączone flagi, ograniczoną rolę bazy, odrzucenie konfiguracji zdalnej lub produkcyjnej, brak ujawnienia sekretów, zamykanie połączeń i przywracanie środowiska po błędzie startu. `git diff --check`: PASS.

Nie wykonano połączenia do VPS ani zmian jego konfiguracji. Poprzednie zaliczone wyniki pełnej regresji pozostają dowodem dla ich poprzedniej wersji; nowa zmiana ma osobny przebieg CI.
