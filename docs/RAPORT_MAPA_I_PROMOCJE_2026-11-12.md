# WiejskaPaka — mapa sprzedawcy i promocje punktów

Kontynuacja raportu `RAPORT_OSTATNIE_POPRAWKI_2026-11-12.md`. Zaimplementowano
pozostające tam wymagania 3 i 6. Kod działa lokalnie; pełne wyszukiwanie nowych
adresów wymaga skonfigurowanego geokodera. Nie deklarujemy odbioru zewnętrznej
usługi, publikacji środowiska ani gotowości produkcyjnej.

Gałąź: `codex/demo-finalization-fixes-20261112`.

- `2eb542bee526266ae87aa21af28e147c05c79c69` — implementacja, migracja i testy.
- `94366772022163ffa42c00a61a3350b924f67b88` — zachowanie dokładnych bajtów
  pakietów mapowych przy odtwarzaniu plików przez Git. Weryfikacja po eksporcie
  z commitu także przeszła; uniknięto rozbieżności checksumów przez CRLF/LF.

Nie zmieniano main, VPS, danych produkcyjnych, sekretów, prawdziwego PayU,
maila ani banku. Commitów nie wysyłano do origin i nie publikowano środowiska.

## Lokalizacja sprzedawcy

W formularzach dodawania i edycji punktu są teraz wyszukiwanie adresu, wybór na
mapie i GPS za zgodą. Nowy punkt przesyła wybraną lokalizację do istniejącego
API; formularz nie wymaga ręcznego wpisywania współrzędnych. Edycja zachowuje
istniejące blokady zmiany miejsca przy niezakończonych zamówieniach.

Mapa poglądowa używa lokalnych Leaflet 1.9.4 i granic państw Natural Earth.
Nie potrzebuje CDN, tokenu, Node.js ani dostępu do usług zewnętrznych. Można
kliknąć miejsce lub przesuwać mapę strzałkami i wybrać jej środek. Granice państw
są poglądowe: mapa lokalna nie pokazuje ulic, działek ani dokładnych adresów.
GPS lub wynik geokodera pozwala ustawić dokładniejszą lokalizację.

Szczegółowe kafelki OpenStreetMap włączane są osobnym przyciskiem z informacją
o przekazaniu widocznego obszaru. Zachowano atrybucję, HTTPS, referrer zawierający
wyłącznie origin i ograniczenie CSP do jednego hosta obrazów
`tile.openstreetmap.org`; nie dodano zewnętrznych skryptów ani unsafe-eval.
Przy błędzie pobrania mapy ulic pozostają mapa lokalna i wybór GPS/adresu.

Wyszukiwanie używa istniejącego API geokodowania:

- przy skonfigurowanej własnej/zakontraktowanej usłudze Nominatim wyszukuje adresy;
- bez niej wyszukuje zapisane publiczne punkty z lokalizacją i udostępnia mapę/GPS;
- adres trafia do geokodera wyłącznie po kliknięciu wyszukiwania, bez tokenu konta;
- zmiana adresu unieważnia poprzedni wybór, a odpowiedzi z wcześniejszej sesji
  nie zapisują miejsca na nowym koncie.

**Stan usług w tej sesji:** `WP_ENABLE_ADDRESS_SEARCH` i `WP_ADDRESS_SEARCH_URL`
nie są ustawione. Nie wymyślano adresu serwera ani kluczy. Kontrakt geokodera
sprawdzono w testach z kontrolowaną odpowiedzią, nie z rzeczywistym usługodawcą.
Próba pobrania kafelka OSM w środowisku została odrzucona HTTP 403; nie uznajemy
jej za dowód awarii OpenStreetMap. Test przeglądarkowy sprawdza działający fallback.
Do pełnej wyszukiwarki operator może skonfigurować obsługiwaną usługę HTTPS przez
istniejące zmienne i zapewnić jej dostęp sieciowy. Nie wpisywać kluczy do repozytorium.

Licencje i wersje pakietów są w `web/LEAFLET-LICENSE.txt`,
`web/WORLD-ATLAS-LICENSE.txt` i `web/MAP-ASSETS.json`. Wszystkie trzy archiwa npm
porównano z opublikowanymi sumami SHA-512 przed przygotowaniem zasobów. Plik
GeoJSON wygenerowano z `world-atlas@2.0.2/countries-110m.json` przez
`topojson-client@3.1.0`; narzędzie konwersji nie jest zależnością aplikacji.

## Kod na trzy darmowe punkty

Administrator tworzy kod, ustala datę końcową (np. 31.12.2026), limit liczby kont
i aktywność. Może później zmienić te ustawienia; nie może obniżyć limitu poniżej
liczby realizacji. Daty obowiązują włącznie z wybranym dniem, według czasu polskiego.

Sprzedawca realizuje kod w profilu gospodarstwa. Jedno konto otrzymuje z danego
kodu dokładnie trzy uprawnienia. Powtórzenie, także równoległe, zwraca istniejący
przydział bez zwiększania limitu i bez kolejnych trzech punktów. Inne konto nie
widzi cudzego przydziału. Kod wygasły, nieaktywny lub wyczerpany nie daje nowego
przydziału.

Utworzenie nowego punktu zużywa jedno ważne uprawnienie w **tej samej transakcji**
co zapis punktu, współrzędnych i kalendarza. Stosowane są blokady konta i kodu oraz
unikalne powiązania. Nieudana transakcja nie zostawia punktu i nie zużywa uprawnienia.
Sześć równoległych zapisów przy jednym przydziale oznacza dokładnie trzy punkty
promocyjne. Wyłączenie punktu nie odnawia już użytego uprawnienia.

Warunki już przyznanego uprawnienia zachowują jego pierwotny termin. Wyłączenie
kodu lub zmiana daty przez administratora dotyczy nowych realizacji kodu, nie
odbiera wcześniej przyznanych praw. Po terminie nie można zużyć niewykorzystanych
uprawnień, ale nie uruchamia się automatycznych opłat ani dezaktywacji punktów.
Dotychczasowy model demo nie pobiera opłat również za punkty poza promocją;
nie wprowadzano cennika ani mechanizmu obciążania konta bez wymagań właściciela.

## Migracja

Nowy `database/optional_pickup_promotions.sql` dodaje:

- `pickup_promo_codes` — ustawienia i licznik realizacji;
- `pickup_promo_grants` — własny przydział, pierwotny termin, pozostałe uprawnienia;
- `pickup_promo_points` — trwałe powiązanie punktu z wykorzystanym uprawnieniem.

Dodano migrację do manifestu, blokady checksumów, przykładu tworzenia nowej bazy
oraz odczytu gotowości. Poprzednich migracji nie zmieniono. Manifest zawiera 42
pliki i został zweryfikowany; wszystkie zastosowano w lokalnych bazach PostgreSQL.
Rola aplikacji potrzebuje SELECT/INSERT/UPDATE na kodach i przydziałach oraz
SELECT/INSERT na powiązaniach punktów; nie potrzebuje DELETE dla tych tabel.
**Nie migrowano VPS.** Przykład dla nowej bazy nie służy do ponownego wykonania
wszystkich migracji na istniejącej bazie produkcyjnej.

## Nowe wyniki testów

| Zestaw | PASS | FAIL | SKIP |
| --- | ---: | ---: | ---: |
| Nowe promocje HTTP/SQLite i mapa/promo w Chromium | 17 | 0 | 0 |
| Pełny natywny moduł PostgreSQL 17.11 | 95 | 0 | 0 |
| Istniejąca regresja Chromium, kalendarza, zdjęć i Kontaktu | 32 | 0 | 0 |
| Izolowana regresja SQLite, 21 modułów | 143 | 0 | 0 |
| Schemat, adresy, gotowość i nagłówek | 45 | 0 | 0 |
| Integralność zasobów mapy | 2 | 0 | 0 |
| Ta sama integralność po eksporcie z Git | 2 | 0 | 0 |

Nowe 17 przypadków obejmuje 12 testów HTTP/SQLite i 5 przeglądarkowych.
Dodatkowo rzeczywiście uruchomiony launcher `--full-demo` zwrócił 200 dla health
i lokalnego podkładu mapy oraz 201 dla utworzenia kodu, jego realizacji i zapisu
punktu z lokalizacją i kalendarzem. Pozostały 2 uprawnienia. Po zatrzymaniu
launchera prywatny plik wygenerowanych kont został usunięty.
Zestawy częściowo się pokrywają — nie sumować ich jako unikalnych przypadków.
Dowody, checksumy JUnit, lista izolowanych modułów i ograniczenia:
`docs/audits/map_promotions_20261112/results.json`.

Sprawdzono m.in. trwałość po restarcie, granicę daty, cztery konta konkurujące
o ostatnią realizację kodu, powtórne użycie przez to samo konto, równoległe
zużywanie trzech uprawnień, rollback po wymuszonym błędzie zapisu, brak dostępu
cudzych kont oraz pełną ścieżkę administrator → kod → sprzedawca → punkt.
Testy mobilne i desktopowe mają szerokości 320 i 1280 px. Kalendarz nadal zapisuje
wybrane dni po rozwinięciu panelu; test dostosowano do obowiązujących ustawień
zwinięcia paneli, zachowując wcześniejsze asercje.

Nie uruchamiano pełnego wielotysięcznego zestawu projektu, Windows, PostgreSQL 16
ani odbioru na fizycznym telefonie. Ostrzeżenie Starlette o deprecjacji integracji
z httpx nie jest błędem testów; nie zmieniano zależności poza zakresem zadania.

## Odbiór lokalny

W aktywnym venv, z katalogu projektu:

```sh
python scripts/run_phone_demo.py --full-demo
```

1. Zaloguj administratora z wygenerowanych, fikcyjnych kont. W „Kody na trzy
   darmowe punkty” utwórz kod z przyszłą datą i limitem kont.
2. Przejdź na sprzedawcę, rozwiń profil gospodarstwa i zrealizuj kod. Powtórz ten
   sam kod: saldo uprawnień nie wzrośnie powyżej trzech.
3. Uzupełnij nowy punkt, wybierz miejsce na mapie lub GPS i zapisz. Sprawdź
   informację o terminie promocji oraz zmniejszone saldo uprawnień.
4. Edytuj własny punkt na mapie. Dla punktu z niezakończonymi zamówieniami zachowana
   blokada zmiany miejsca jest oczekiwanym zachowaniem.
5. Opcjonalnie włącz mapę ulic. Jeżeli sieć jej nie dopuszcza, sprawdź komunikat
   i dalsze działanie lokalnej mapy. Dowolne nowe adresy wyszukuj dopiero po
   konfiguracji geokodera; bez niej dostępne są zapisane punkty, mapa i GPS.

Do powtórzenia nowych testów:

```sh
python -m pytest -q tests/test_pickup_promotions_http.py tests/test_pickup_map_promotions_browser.py tests/test_pickup_map_assets.py
python -m database.verify_test_migrations
python -m pytest -q tests/test_postgres_full_api_optin.py
```

Ostatnie polecenie wymaga własnego `WP_TEST_POSTGRES_DSN` dla jednorazowego,
lokalnego klastra, zgodnie z zabezpieczeniami modułu. Bez DSN zostanie pominięte;
w tej sesji rzeczywiście wykonano 95 przypadków. Nie używać DSN VPS.
