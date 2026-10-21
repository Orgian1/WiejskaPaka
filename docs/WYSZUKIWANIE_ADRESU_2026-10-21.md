# Wyszukiwanie adresu — etap lokalny

Dodano formularz miejscowości, opcjonalnej ulicy/numeru i kodu pocztowego.
Po kliknięciu „Znajdź adres” użytkownik wybiera jeden z maksymalnie pięciu
wyników. Nie wybieramy automatycznie pierwszego wyniku. Edycja adresu usuwa
wybrane współrzędne i wyniki ofert. Spóźnione odpowiedzi i odpowiedzi z poprzedniej
sesji są ignorowane. Lokalizacja urządzenia pozostaje osobną możliwością.

Funkcja jest domyślnie wyłączona. Bez konfiguracji pozostaje wcześniejszy formularz
współrzędnych i lokalizacja urządzenia. Nowego formularza nie wdrożono na VPS.

## Konfiguracja po wyborze dostawcy

- `WP_ENABLE_ADDRESS_SEARCH=1`
- `WP_ADDRESS_SEARCH_URL`: pełny adres HTTPS endpointu wyszukiwania własnego lub
  zakontraktowanego serwera zgodnego z Nominatim (format JSONv2).

Nie ma domyślnego dostawcy. Publiczne hosty openstreetmap.org są odrzucane.
Nie wpisywać loginów, haseł ani tokenów w URL. Klient nie może podać URL
dostawcy w zapytaniu. Nie zakupiono ani nie aktywowano żadnej usługi.
Przed aktywacją ustalić limity i ochronę przed nadużyciami dla całej instalacji
oraz warunki dostawcy dotyczące przesyłania adresów i przechowywania logów.

API otrzymuje adres przez POST `/address-search`. Do dostawcy trafia wyszukiwanie
strukturalne (city, opcjonalnie street/postalcode), ograniczone do Polski.
Adres nie jest zapisywany w bazie ani localStorage. Przeglądarka nie umieszcza
go w URL. Dostawca otrzymuje parametry adresowe w swoim żądaniu GET; polityka
logów dostawcy wymaga osobnej weryfikacji. Timeout 5 s, maksymalnie 64 KiB,
brak przekierowań, brak przekazywania tokenu konta użytkownika.

Wyniki są prezentowane tekstowo; współrzędne orientacyjne (np. środek miasta)
nie są przedstawiane jako potwierdzony dokładny adres. Formularz zawiera
atrybucję OpenStreetMap. Nie ma autocomplete ani zewnętrznych map/telemetrii.

## Walidacja

51 testów zaliczonych w izolowanym zestawie adresów, interfejsu pobliskich ofert,
inwentaryzacji autoryzacji i znaczników mobilnych. Testy transportu używają
MockTransport; test interfejsu używa izolowanego środowiska DOM/Node.
Nie wykonywano rzeczywistych zapytań adresowych ani testów w przeglądarce.
Pełna wcześniejsza regresja 4142 passed opisuje wersję sprzed tej zmiany.

Źródła kontraktu i ograniczeń:
- https://nominatim.org/release-docs/latest/api/Search/
- https://operations.osmfoundation.org/policies/nominatim/

Pełna regresja po poprawce zmiany adres/GPS (commit 7ef5825): 4176 passed, 0 failed, 68 skipped; 332/332 moduły. Wszystkie części mają zgodny fingerprint i niezmienione źródła. Raporty w docs/audits/address_search_2026-10-21/. Nadal bez prawdziwego dostawcy i wdrożenia VPS.
