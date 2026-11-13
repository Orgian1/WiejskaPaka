# WiejskaPaka — przygotowanie do odbioru właściciela, 13.11.2026

Repozytorium: `Orgian1/WiejskaPaka`.
Gałąź: `codex/demo-finalization-fixes-20261112`.
Baza pakietu: `2fe1895f3191c76881d9d780b0b935cafcf47442`.
Końcowy SHA pakietu podano w odpowiedzi po zapisie i push; dowody niżej zawierają
hashe dokładnie testowanych źródeł. Nie zmieniano main, VPS ani danych produkcji,
nie publikowano środowiska i nie podłączano prawdziwych płatności.

## Zmiany

Kolejność punktów sprzedawcy jest teraz zapisywana w bazie na koncie, zamiast
wyłącznie w localStorage. Nowe GET/PUT `/farmers/me/navigation` wymagają sesji
sprzedawcy; nie przyjmują identyfikatora innego konta. Walidują własność punktów,
duplikaty i wersję zapisu. Dwa jednoczesne zapisy tej samej wersji kończą się
jednym sukcesem i jednym 409, również na PostgreSQL. Interfejs wyjaśnia konflikt
i pobiera aktualną kolejność; można ją też odświeżyć przyciskiem. Zmiana konta
czyści stan, a opóźnione odpowiedzi nie przenoszą listy do innej sesji.

Nowa migracja: `database/optional_seller_navigation.sql`. Manifest obejmuje teraz
44 pliki; wcześniejsze 43 pliki SQL i ich sumy pozostały niezmienione. Dodano
kontrolę tabeli przy starcie oraz testy prywatności, współbieżności, restartu
PostgreSQL i niezależnych kontekstów przeglądarki (320/1280 px). Nowe punkty są
dopisywane na końcu, punkty innych kont nie mogą wejść do listy. Stara kolejność
z localStorage nie jest automatycznie importowana; ustawia się ją raz po aktualizacji.
Nie implementowano ponownie katalogu, ulubionych, mapy ani promocji.

## Photon i działanie przy braku sieci

Zweryfikowano istniejącą konfigurację Photon dla Polski: jawna opcja
`--public-geocoder photon`, język `pl`, `countrycode=PL`, do pięciu wyników.
Publiczna usługa nie wymaga klucza. Pozostawiono limity małego demo i wyszukiwanie
wyłącznie po kliknięciu; nie włączono wysyłania adresów domyślnie dla innych trybów.

Bezpośrednie połączenie do `photon.komoot.io` blokuje proxy środowiska (`403`).
Rzeczywisty launcher `run_phone_demo.py --full-demo --public-geocoder photon`
uruchomiono z prywatnym plikiem fikcyjnych kont: health 200, geokoder włączony,
wyszukiwanie zwraca kontrolowane 503. W tej samej mobilnej sesji Chromium
potwierdzono komunikat o mapie/GPS, wybór punktu na lokalnej mapie, następnie GPS
za zgodą (emulowana lokalizacja), brak błędów JS i brak poziomego overflow.
Leaflet jest dostarczany lokalnie (HTTP 200). Niedostępność Photon nie zatrzymuje
wyboru punktu. Nie potwierdzono pozytywnego wyniku rzeczywistego publicznego
geokodowania; transport i poprawne polskie wyniki sprawdzono testami kontrolowanymi.

## Końcowe wyniki tego pakietu

| Zestaw | PASS | FAIL | SKIP |
| --- | ---: | ---: | ---: |
| Izolowane API/SQLite, Photon, migracje i prywatność — 15 modułów | 97 | 0 | 0 |
| Wybrane natywne testy PostgreSQL: nawigacja/restart, ulubione i promocje | 3 | 0 | 0 |
| Rozszerzony zestaw przeglądarkowy | 101 | 0 | 0 |
| Osobna kontrola zdjęć w przeglądarce | 2 | 0 | 0 |

PostgreSQL: 96 pozostałych przypadków modułu nie wybrano w tym przebiegu; nie
zalicza się ich do PASS ani SKIP. Wynik 4889 PASS / 0 FAIL / 105 SKIP pozostaje
historyczną pełną regresją poprzedniego pakietu. Nie ogłaszamy go nową pełną
regresją. Powtarzających się przypadków między zestawami nie należy sumować jako
unikalnych testów.

Natywny zestaw przeglądarkowy zakończył się `success=true` i
`sources_unchanged=true`. Obejmuje rzeczywiste HTTP/SQLite i logowanie, działanie
paneli oraz wylogowanie klienta, sprzedawcy, dostawcy i administratora przy 320
oraz 1280 px; ponadto testy tras, katalogu, odbioru, dat, portfela, mapy i promocji.
Kontrola aplikacji przez HTTP/Chromium przy szerokościach 320, 360, 390, 768 i
1280 px również zakończyła się sukcesem. Potwierdzono manifest i sumy 44 migracji,
składnię zmienionego JS oraz `git diff --check`.

Dowody bez surowych logów, haseł i danych kont:
`docs/audits/owner_acceptance_20261113/`.
Nie wykryto otwartego błędu aplikacji w wykonanych scenariuszach.

## Dokumenty do odbioru i dalsze ograniczenia

- [Prosta instrukcja uruchomienia i lista odbioru](ODBIOR_WLASCICIELA_2026-11-13.md)
  opisuje cztery konta, kolejność czynności, Photon i tryb bez dostępu do usługi.
- [Bezpieczna procedura VPS](AKTUALIZACJA_VPS_ODBIOR_2026-11-13.md) obejmuje
  inwentaryzację, szyfrowaną kopię, rzeczywistą próbę odtworzenia, plan brakujących
  migracji, nowy podgląd obok obecnego oraz rollback z ochroną nowych operacji.
  Jest przygotowana do przeglądu przez operatora; nie została wykonana na VPS.
- Nie wykonano odbioru na fizycznym telefonie ani Windows. Testy dotyku i GPS są
  emulowane w Chromium. Fizyczny telefon wymaga bezpiecznego połączenia HTTPS
  i zgody GPS; lokalny launcher nie wystawia portu publicznie.
- Publiczny Photon i szczegółowe kafelki OSM wymagają dostępnej sieci. Cloud proxy
  pozostaje blokadą Photon. Dla większego użycia potrzebny jest własny Photon.
- Demo jest jednorazowe: restart launchera tworzy nowe konta i bazę. Synchronizacja
  dwóch urządzeń wymaga tej samej działającej instancji i tego samego konta.
  Trwałość po restarcie aplikacji potwierdzono na testowym PostgreSQL.
- Stan i zgodność obecnej bazy VPS wymagają osobnej kontroli operatora przed
  ewentualną aktualizacją. Nie wykonywać całego bootstrapu nowej bazy na istniejącej.
