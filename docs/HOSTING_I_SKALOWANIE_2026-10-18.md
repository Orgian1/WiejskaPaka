# Hosting WiejskaPaki i wzrost ruchu — 18.10.2026

## Dobór na start

Rekomendowany kandydat do zamkniętego testu: OVHcloud VPS-3, x86-64 Linux,
6 vCores, 12 GB RAM, 100 GB NVMe, 2 Gbps; oferta publiczna od 44,37 zł netto
/ 54,58 zł brutto miesięcznie. Dla porównania VPS-2: 4 vCores / 8 GB /
75 GB / od 37,85 zł brutto; VPS-4: 8 vCores / 24 GB / 200 GB /
od 104,65 zł brutto. To ceny „od”, nie wiążący koszt zamówienia ani odnowienia.
Przed zakupem sprawdzić okres zobowiązania, region, cenę odnowienia i opcje.
Nie zakupiono ani nie uruchomiono płatnej usługi.

Wybrać zwykłe centrum danych UE. Local Zones mają ograniczenia dodatkowych
usług i migracji; nie traktować wszystkich lokalizacji jako zamiennych.
VPS jest samodzielnie administrowanym serwerem: aktualizacje, konfiguracja
aplikacji i PostgreSQL nie są automatycznie zapewniane przez zakup.

Na pierwszym serwerze zamkniętego testu: reverse proxy HTTPS, aplikacja,
PostgreSQL i monitoring. Baza nie powinna być publicznie dostępna.
Jedna maszyna oznacza wspólny punkt awarii; nie zapewnia wysokiej dostępności.
Kopia PostgreSQL poza serwerem i próba odtworzenia są osobnym wymaganiem.
Nie utożsamiać codziennej kopii VPS z pełną strategią ochrony bazy.
Planistyczna rezerwa startowa 100–200 zł brutto miesięcznie obejmuje serwer
oraz miejsce na dodatkowe kopie i monitoring; to nasz budżet, nie oferta dostawcy.
Poczta, praca administratora i przyszłe prowizje płatności nie są wycenione.

## Jawne założenia ruchu

Rolnik i sprzedawca to ta sama rola. Klienci dzienni nie oznaczają klientów
jednoczesnych ani liczby transakcji. Przyjęto 20 żądań API na klienta;
prawdziwy ruch, zdjęcia, boty i działania sprzedawców trzeba zmierzyć osobno.

| Parametr | Start | Rozbudowa |
| --- | ---: | ---: |
| Sprzedawcy | 50 | 5000 |
| Klienci dziennie | 5000 | 500000 |
| Żądania dziennie przy założeniu 20/klienta | 100000 | 10000000 |
| Średnia na sekundę przy równym rozłożeniu przez 24 h | 1,16 | 115,74 |
| Średnia godziny szczytu przy 20% ruchu w tej godzinie, zaokrąglona w górę | 6 | 556 |

Ostatni wiersz to ostrożniejsze założenie planowania, nie deklaracja
jednoczesności ani zmierzona zdolność aplikacji. Nawet równy ruch w ciągu dnia
może zawierać krótkie skoki. Kalkulator: `python scripts/report_capacity_target.py`.

## Ścieżka rozbudowy

1. Zamknięty test na VPS-3: pomiar rzeczywistego HTTP i PostgreSQL z 50
   sprzedawcami i realistyczną liczbą ofert, zakupów i sesji. Nie przenosić
   wyników lokalnego SQLite na wybrany serwer.
2. Po pomiarach można zwiększyć zasoby VPS. Dostawca oferuje powiększanie
   konfiguracji, ale nie zastępuje to optymalizacji zapytań i indeksów.
3. Przed dużą kampanią oddzielić bazę od aplikacji, a pliki od dysku aplikacji;
   wprowadzić magazyn obiektowy/CDN i kolejkę prac dla poczty.
4. Kandydat do testu skali 500000/dzień: load balancer, 2–4 instancje aplikacji
   po 4–8 vCPU i 8–16 GB RAM, osobny PostgreSQL 8–16 vCPU / 32–64 GB RAM,
   pula połączeń i kopie poza serwerem. To hipoteza do pomiaru, nie gwarancja
   ani finalny kosztorys. Dostępność wymaga także planu awarii bazy i jej
   ewentualnej repliki; sam load balancer nie chroni pojedynczej bazy.
5. Rozbudowa do klastra wymaga przygotowania aplikacji: współdzielonych sesji,
   spójnych kluczy szyfrowania, centralnych limitów prób, braku zależności od
   lokalnego SQLite, kontroli współbieżnych zapisów i idempotencji. Sama
   zmiana planu VPS nie wykonuje tych prac i nie uruchamia autoskalowania.

OVHcloud oferuje Public Cloud Load Balancer i zarządzany PostgreSQL.
Przejście z VPS do Public Cloud to osobne wdrożenie/migracja, nie obietnica
zamiany jednego planu jednym kliknięciem. Hetzner Cloud jest alternatywą
z load balancerem i serwerami w UE; odczytane strony nie ujawniły pełnych
cen dynamicznych i pokazały niedostępność części tanich instancji, dlatego
nie podano ich jako potwierdzonej dostępnej oferty cenowej.

## Warunki odbioru

Na docelowej infrastrukturze zmierzyć p50/p95/p99, błędy, CPU, RAM, dysk,
połączenia i blokady PostgreSQL, opóźnienie kolejki oraz wielkość transferu.
Sprawdzić katalog, logowanie, zakup ostatniej sztuki, ponowienia, PIN,
zwroty testowe i restart. Obciążenie ma obejmować odczyty oraz zapisy.
Zwiększać do 6 żądań/s na start oraz 556 żądań/s dla założonego szczytu
rozbudowy; oddzielnie mierzyć skoki i dłuższy stabilny przebieg.
Testy skali uruchamiać wyłącznie na własnym izolowanym środowisku testowym.
Nie uruchomiono takiego testu na komercyjnym serwerze. `capacity_verified`
pozostaje fałszywe. Nie certyfikuje się skali na podstawie liczby kont.

## Źródła ofert, odczyt 18.10.2026

- https://www.ovhcloud.com/pl/vps/ — parametry, ceny „od”, kopie, Local Zones.
- https://www.ovhcloud.com/pl/public-cloud/load-balancer/ — rozdzielanie ruchu.
- https://www.ovhcloud.com/pl/public-cloud/postgresql/ — zarządzana baza.
- https://www.hetzner.com/cloud/cost-optimized/ — alternatywa i ograniczenia dostępności.
- https://www.hetzner.com/cloud/load-balancer/ — podział ruchu i kontrole zdrowia.

## Weryfikacja bieżącego pakietu

Poprzednia pełna regresja poprawki historii: 3802 zaliczone, 0 błędów,
40 pominiętych, 313/313 modułów; dotyczy kodu przed rozszerzeniem kalkulatora.
Zmiany obecnego pakietu dotyczą wyłącznie planowania skali i dokumentacji.
Testy celowane kalkulatora, CLI, planu obciążenia i historii UI:
19 zaliczonych, 0 błędów, 0 pominiętych; ponadto 13 podprzypadków unittest. Starszych testów natywnych nie
przypisuje się nowemu zestawowi źródeł. Integracje produkcyjne i płatności
pozostają wyłączone.
