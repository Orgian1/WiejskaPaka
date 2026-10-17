# Wyszukiwanie lokalne i punkty odbioru

## Przepływ użytkownika

W sekcji **Blisko mnie** klient podaje produkt, współrzędne i promień
100 m / 500 m / 1 km / 5 km. Opcjonalnie ogranicza cenę w złotych. Może też
kliknąć przycisk bieżącej lokalizacji urządzenia; dopiero to kliknięcie
uruchamia prośbę przeglądarki o zgodę. Odmowa pozostawia możliwość ręcznego
wpisania współrzędnych. Lokalizacja urządzenia wymaga bezpiecznego kontekstu
przeglądarki, np. loopback podczas lokalnego testu.

Wynik przedstawia produkt, cenę w groszach sformatowaną na złote, dostępność,
odległość oraz jeden konkretny aktywny punkt z adresem i godzinami. Produkty
rolnika są dostępne we wszystkich jego aktywnych punktach; stan magazynowy
pozostaje wspólny dla produktu, a nie osobny dla każdego punktu.
Najbliższe oferty są pierwsze; remisy rozstrzyga ID punktu i produktu.
Następna strona ma maksymalnie 24 pozycje w interfejsie. Brak pozycji nie
powoduje automatycznego rozszerzenia promienia bez wiedzy użytkownika.

Zalogowany klient dodaje produkt do istniejącego koszyka. Punkt wybiera jawnie
przy zamówieniu. Wyszukiwanie nie rezerwuje towaru i nie gwarantuje dostępności
przy późniejszym zakupie. Checkout ponownie sprawdza magazyn i aktywność punktu.
Wszystkie wcześniejsze reguły dostawy, PIN-u, anulowań i zwrotów są zachowane.

## Zarządzanie punktami

Rolnik tworzy punkt jak wcześniej, a w panelu **Zarządzaj punktami odbioru**
ustawia jego współrzędne. Punkt bez współrzędnych pozostaje dostępny w zwykłym
wyborze odbioru, lecz nie pojawia się w wynikach odległości. Nie zgadujemy
współrzędnych z adresu i nie wywołujemy zewnętrznego geokodera.

Właściciel może atomowo edytować nazwę, miejscowość, adres, godziny, aktywność
i współrzędne. Usunięcie współrzędnych wymaga jawnego pola
`clear_coordinates`; pominięcie współrzędnych w żądaniu ich nie usuwa.
Wyłączenie punktu blokuje nowe zakupy i usuwa go z wyszukiwania. Wcześniejsze
zamówienia nadal można zrealizować i potwierdzić PIN-em.

Jeśli istnieje niezakończone zamówienie odbioru (oczekujące lub gotowe),
nie można zmieniać nazwy, miejsca, godzin ani współrzędnych punktu. Nie wolno
w ten sposób przenieść uzgodnionego odbioru. Wyłączenie nowych zakupów nadal
jest dozwolone. Odpowiedź 409 wyjaśnia tę regułę. Wszystkie pola i lokalizacja
zapisują się w jednej transakcji; niepowodzenie zapisu wycofuje całość.

## API

- `POST /marketplace/nearby`: publiczna, wyłącznie odczytowa operacja. Body:
  `latitude_e6`, `longitude_e6`, `radius_m`, `q`, opcjonalne
  `min_price_grosze`, `max_price_grosze`, `limit` (1–100), `offset` (0–10000).
  Współrzędne i kwoty wymagają ścisłych integerów. Dozwolone promienie to
  dokładnie 100, 500, 1000, 5000 metrów. Odpowiedź zawiera `items` i `has_more`.
- `POST /pickup-points`: dotychczasowe pola, opcjonalnie obie współrzędne.
- `PUT /pickup-points/{point_id}`: wyłącznie właściciel będący rolnikiem;
  pełne pola punktu, ścisły bool `active`, opcjonalnie współrzędne lub jawne
  `clear_coordinates: true`. Cudzy punkt zwraca 404.
- `GET /farmers/me/pickup-points`: właściciel widzi także współrzędne i aktywność.
- `/catalog/search`: wyszukiwanie nazw również korzysta z indeksu polskich nazw.

`latitude_e6` oznacza stopnie pomnożone przez 1 000 000: 52,229676° to
52229676. Zakresy: szerokość ±90°, długość ±180°. Polskie litery i wielkość
znaków nie przeszkadzają wyszukiwaniu, np. `ŁĄKOWE` pasuje do `lakowe`.
Znaki `%`, `_` i ukośnik są wyszukiwane dosłownie, a nie jako wzorce SQL.
Zmiana nazwy produktu i jego indeksu odbywa się w jednej transakcji.

## Prywatność

Pozycja klienta jest przesyłana w body POST, bez umieszczania w adresie URL.
Publiczne zapytanie interfejsu nie przesyła tokenu konta. Odpowiedzi mają
`no-store`; aplikacja nie zapisuje pozycji klienta w bazie, historii, localStorage
ani sessionStorage. Wyszukiwanie nie wymaga logowania. Przycisk czyszczenia,
wylogowanie i zmiana konta usuwają współrzędne i wyniki z bieżącego interfejsu.
Przestarzałe odpowiedzi i spóźnione wyniki GPS nie przywracają tych danych.

Permissions-Policy dopuszcza geolokalizację wyłącznie dla własnego originu.
Kamera, mikrofon i płatności urządzenia pozostają zablokowane. Brak zewnętrznych
map, analityki i usług lokalizacyjnych w kodzie tej funkcji. Współrzędne punktu
rolnika są trwałymi danymi punktu; panel wyraźnie informuje o publicznym adresie.
To nie zastępuje przeglądu prawnego i konfiguracji retencji logów infrastruktury.

## Model odległości i granice

Używamy przybliżonej odległości po sferze o promieniu 6 371 008,8 m, w linii
prostej, bez tras drogowych. SQL porównuje odległości cięciw na sferze,
obliczone z wektorów punktów. Nie wymaga PostGIS ani dodatków. Indeksy
współrzędnych wektora ograniczają zbiór kandydatów; wynik jest sortowany
przed paginacją. Bieguny i przekroczenie południka 180° są obsługiwane.

Współrzędne API są integerami z dokładnością do mikrostopnia. Wektory i geometria
używają liczb zmiennoprzecinkowych; **żadna kwota ani obliczenie pieniężne nie
używa tych liczb**. Odległość wyświetlamy jako całkowite metry zaokrąglone w górę.
GPS, model sferyczny i brak tras oznaczają, że nie jest to gwarancja drogi dojazdu
ani pomiar geodezyjny. Dostępność i kolejność mogą zmienić się między stronami.

## Migracja i testy

SQLite tworzy nowe tabele przy imporcie. PostgreSQL wymaga uprzedniego
zastosowania `database/upgrade_b10921_local_marketplace.sql` w bazie testowej.
Rola aplikacyjna nadal nie tworzy tabel. Start procesu sprawdza schemat i
uzupełnia indeks nazw starszych produktów. Po ręcznym imporcie/zmianach SQL
należy ponownie uruchomić aplikację, aby odświeżyć indeks. Zwykłe zmiany przez
API aktualizują go automatycznie. Punktom nie nadaje się współrzędnych wstecz.

```bash
python scripts/run_tests_per_file.py test_local_marketplace.py test_local_marketplace_ui.py test_local_marketplace_http.py --report lokalne_testy.json
python scripts/check_local_marketplace_http.py --report lokalne_http.json
python scripts/benchmark_local_search.py --report lokalne_skala.json
```

Testy Node uruchamiają rzeczywisty skrypt UI w kontrolowanym środowisku DOM,
fetch i geolokalizacji. Nie są testem natywnego Chromium. Test skali SQLite
porównuje wyniki z niezależnym wzorem haversine dla syntetycznych danych;
jego czasy nie są deklaracją wydajności produkcyjnej. Natywna integracja
PostgreSQL oraz prawdziwe Chromium nadal wymagają odpowiedniego środowiska.
