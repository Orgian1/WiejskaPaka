# WiejskaPaka — regresja pakietu końcowego, 13.11.2026

Repozytorium: `Orgian1/WiejskaPaka`.
Gałąź: `codex/demo-finalization-fixes-20261112`.
Testowany commit aplikacji: `2fda7bc874522acec09a1f4ef1b2bf3e8180cb61`.

## Wykonane prace

Zakończono pełną regresję kodu zapisanego w poprzednim pakiecie. Nie było potrzeby
kolejnych zmian aplikacji: wszystkie wykonane scenariusze przeszły. Zachowano
katalog z rozwijaniem szczegółów pod rzędem i ulubionymi per konto, grupowanie
zamówień sprzedawcy według punktów, domyślne zwijanie paneli, nawigację według
kolejności punktów oraz propozycje terminów dostawy z decyzją klienta.

Testy obejmują również automatyczną akceptację odbioru po płatności testowej,
jednorazowy PIN przesyłki, prywatność danych i regresję wcześniejszych funkcji
mapy oraz administracyjnych kodów na trzy punkty.

## Wyniki

| Zestaw | PASS | FAIL | SKIP |
| --- | ---: | ---: | ---: |
| Pełna regresja w izolowanych procesach, 397 modułów | 4889 | 0 | 105 |
| PostgreSQL 17.11 — pełne API | 98 | 0 | 0 |
| PostgreSQL — konfiguracja i transakcje | 4 | 0 | 0 |
| Rozszerzone testy przeglądarkowe | 99 | 0 | 0 |
| Osobna kontrola zdjęć w przeglądarce | 2 | 0 | 0 |

Wszystkie cztery części pełnej regresji zakończyły się sukcesem i potwierdziły
niezmienność źródeł. 105 pominięć obejmuje: 102 testy PostgreSQL uruchomione
osobno z wynikiem PASS, jeden rozszerzony scenariusz przeglądarkowy uruchamiany
osobno oraz dwa testy odmowy dostępu na platformie innej niż POSIX. Te dwa
ostatnie nie zostały wykonane na Linuksie.

Kontrola aplikacji przez HTTP i Chromium przy pięciu rozmiarach ekranu również
zakończyła się sukcesem. Rozszerzony zestaw potwierdził niezmienność źródeł.

Sprawdzono manifest i sumy kontrolne 43 plików migracji. Nową migrację propozycji
terminów dostawy wykonano w jednorazowych bazach testowych PostgreSQL, wraz
z testami SQLite. Nie wykonywano migracji na VPS.

Dowody: `docs/audits/final_package_20261113/`. Raporty zawierają wyniki i hashe,
bez surowych logów, danych kont i poświadczeń. Wyników powtarzających się między
zestawami nie należy dodawać jako liczby unikalnych testów.

## Ograniczenia i odbiór

- Nie testowano fizycznego telefonu ani Windows. Testy mobilne używają emulacji
  ekranu i dotyku Chromium.
- Publiczny Photon i szczegółowe kafelki OpenStreetMap pozostają zależne od
  dostępu sieciowego środowiska. Wcześniej potwierdzono blokadę przez proxy;
  ten przebieg nie potwierdza wyszukiwania adresów w publicznej usłudze.
  Działa lokalna mapa i obsługa zapisanych punktów; GPS wymaga zgody użytkownika.
- Kolejność punktów nawigacji jest zapisywana dla konta w bieżącej przeglądarce;
  nie jest synchronizowana między urządzeniami.
- Testy używają wyłącznie płatności testowych i lokalnych baz. Nie zmieniano
  main, VPS, produkcyjnych sekretów ani prawdziwego PayU. Nie publikowano
  środowiska.

Lokalne demo: `python scripts/run_phone_demo.py --full-demo` w środowisku
z zależnościami z `requirements-lock.txt`. Opcja `--public-geocoder photon`
włącza publiczne wyszukiwanie adresów i wymaga dostępu sieciowego. Pełny pakiet
wdrożeniowy wymaga niezależnego odbioru właściciela; ten raport nie jest wdrożeniem.
