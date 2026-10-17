# WiejskaPaka — duży pakiet lokalny, 16 października 2026

Sprawdzony commit kodu: `f316340c3fd1beb391905faf5600d889e84e9df1`.

Odcisk aplikacji i skryptów: `ea31b0f806193bbf0feec9b2112ce3d057334eef7f602c10a4db7aed670146af`.

## Wynik pakietu

Zintegrowano lokalne wyszukiwanie produktów i aktywnych punktów odbioru,
zarządzanie punktami przez rolnika oraz ochronę lokalizacji klienta. W tej
paczce dodano 70 odrębnych testów. Pracowano bez GitHub zgodnie z poleceniem:
nie łączono repozytorium, nie publikowano danych i nie uruchamiano Actions.

To pełny projekt lokalny, a nie sam plik poprawek. Wersja pozostaje testowa;
nie potwierdzamy gotowości produkcyjnej ani procentu ukończenia aplikacji.

## Zmiany funkcjonalne

1. Sekcja **Blisko mnie** i publiczny `POST /marketplace/nearby`: wyszukiwanie
   produktu dla 100 m, 500 m, 1 km i 5 km, najbliższe oferty jako pierwsze,
   przedziały odległości, cena, stan, nazwa/adres/godziny jednego punktu.
2. Filtry ceny są całkowitymi groszami; wyniki mają ograniczoną paginację.
   Brak wyników, nieprawidłowe dane i błędy sieci mają komunikaty w języku polskim.
3. Polskie znaki i wielkość liter w nazwach: `ŁĄKOWE` pasuje do `lakowe`.
   Dotyczy też zwykłego katalogu. Nazwa i indeks zapisują się atomowo;
   awaria indeksowania wycofuje zmianę produktu.
4. Rolnik ustawia współrzędne punktu, edytuje dane, włącza/wyłącza punkt
   i jawnie usuwa współrzędne. Właściciel ma dostęp wyłącznie do swoich punktów.
5. Wyłączony punkt znika z wyszukiwania i nie przyjmuje nowych zakupów ani
   checkoutu zapisanego koszyka. Wcześniejszy odbiór nadal można potwierdzić PIN-em.
6. Otwarte zamówienie blokuje zmianę uzgodnionego miejsca i godzin odbioru,
   w tym współrzędnych. Nowe zakupy i edycje punktu używają odpowiednich blokad.
7. Wynik wyszukiwania pozwala dodać produkt do istniejącego koszyka. Punkt
   odbioru klient wybiera jawnie przy zamówieniu; dostępność jest sprawdzana ponownie.

## Prywatność i poprawki techniczne

- Współrzędne klienta są w body POST, bez zapisu w bazie, localStorage,
  sessionStorage ani URL. Publiczne wyszukiwanie nie wysyła tokenu konta;
  odpowiedzi mają `no-store`.
- Lokalizacja urządzenia wymaga kliknięcia i zgody przeglądarki; odmowa daje
  możliwość ręcznego wpisu. Permissions-Policy pozwala na GPS tylko własnemu
  originowi. Kamera, mikrofon i płatności urządzenia pozostają zablokowane.
- Wylogowanie, zmiana konta i przycisk czyszczenia usuwają wyniki oraz
  współrzędne. Opóźnione odpowiedzi HTTP i GPS nie przywracają starych danych.
- Renderowanie wyników używa tekstu, nie HTML. Sprawdzono także niebezpieczną
  nazwę produktu, dosłowne znaki SQL LIKE i próby wstrzyknięcia SQL.
- Poprawiono kolejność ładowania nowego skryptu przez `defer`. Zestaw
  testowy sprawdza zależności skryptów oraz faktyczne zachowanie JavaScript.
- Pomocniczy skrypt testów JS jest częścią odcisku źródeł raportu, aby jego
  zmiana unieważniała wcześniejsze wyniki. Dwa stare, minimalne schematy
  testowe dostosowano do nowej tabeli indeksu bez osłabiania asercji.
- PostgreSQL ma jawną migrację; aplikacja nie tworzy tabel rolą użytkową.
  Indeks starszych nazw jest uzupełniany przy starcie, z blokadą produktów
  w natywnej ścieżce PostgreSQL. Ta ścieżka nadal wymaga rzeczywistego testu.

## Faktycznie wykonane testy

| Weryfikacja | Wynik |
|---|---|
| Pełna regresja z czystej kopii śledzonych źródeł | 238 modułów, **3013 PASS, 0 FAIL, 14 SKIP** |
| Nowe przypadki | 55 API/geometria/bezpieczeństwo, 14 UI/markup, 1 rzeczywiste HTTP: razem 70 PASS |
| Rzeczywiste HTTP nowego przepływu | 35 liczonych żądań API, 131 kontrole PASS |
| Stabilność prawdziwego HTTP | 600.23 s, 4708 rund, 36870 żądań, 87248 kontroli PASS |
| Test skali SQLite | 10000 punktów, 40 zapytań, 342880 niezależnych obliczeń haversine, 1116 kontroli PASS |
| Czasy SQL przy tym teście | mediana 0.618 ms, maksimum 2.781 ms; obserwacja tej maszyny, nie obietnica wydajności |
| Anonimowy dostęp HTTP | 80/80 prywatnych tras zablokowanych; 0 niejednoznacznych wyników |
| Dotychczasowy pakiet akceptacyjny HTTP | 4 zadania PASS: loopback, zakup/dostawa/zwrot, wielu sprzedawców, prywatność/dostawa |
| Finanse | 20 001 kwot, 100 002 kontrole PASS z niezależnym wzorcem Decimal |
| Składnia | compileall backend/database/scripts; node --check wszystkich trzech skryptów web: PASS |
| PostgreSQL natywny | NIEZWERYFIKOWANY, 12 pominiętych przypadków |
| Chromium | NIEZWERYFIKOWANY, 2 pominięte przypadki |

SKIP nie jest PASS. Żądań, rund i kontroli nie dodajemy do liczby odrębnych
testów pytest. Przerwane i wcześniejsze raporty nie są dowodem wydania.
Końcowe bramy sprawdzają niezmienność źródeł. Testy Node wykonują rzeczywisty
skrypt UI w kontrolowanym DOM/fetch/GPS; nie są testami prawdziwej przeglądarki.
W teście skali użyto SQLite w pamięci i syntetycznych danych, bez PostgreSQL.

Rzeczywiste HTTP obejmuje: wyszukiwanie we wszystkich promieniach, polskie nazwy,
blokadę cudzej edycji, ochronę otwartego odbioru, wyłączenie punktu, odrzucenie
nowego zakupu, płatność testową i odbiór PIN-em wcześniejszego zamówienia.
Osobno sprawdza koszyk dwóch produktów: 199 + 301 + **jedna dostawa 501** =
1001 gr, pełny zwrot 1001 gr po winie dostawcy i odebranie dostępu do adresu.

## Granice i stan projektu

Nie dodano produkcyjnych płatności, przelewów, banku, hostingu, domeny, Neon
ani usług płatnych. Nie dodano pól numerów telefonów. Wszystkie kwoty i
obliczenia pieniężne pozostają całkowitymi groszami. Geometria używa float
wyłącznie do odległości i wektorów; nie do pieniędzy. Prawa konsumenta
pozostają zachowane w istniejącym komunikacie i nie są ograniczane PIN-em.

Pomiar jest przybliżeniem sferycznym w linii prostej, bez tras drogowych.
Punkty bez współrzędnych nie są zgadywane ani geokodowane. Stan produktu
jest wspólny dla punktów tego samego rolnika. Zewnętrzne mapy i rzeczywisty
GPS telefonu nie zostały przetestowane. Test 10 tys. punktów nie potwierdza
wydajności całej produkcyjnej infrastruktury.

PostgreSQL i Chromium pozostają niezweryfikowane z powodu znanych ograniczeń
środowiska; nie ponawiano identycznych nieskutecznych prób ani nie zaliczano
ich zastępczo przez SQLite/Node. Dodano natywny test nowej funkcji, ale ma SKIP.

Blokada edycji chroni otwarte odbiory. Pełna, niezmienna historia pierwotnego
adresu i godzin punktu po zakończeniu zamówienia nadal wymaga osobnego modelu.

Pozostałe istotne prace: weryfikacja sprzedawcy i bezpieczna obsługa danych
urzędowych/bankowych, opłaty punktów i roczne rozliczenie kosztów, ochrona i
retencja testowego PIN-u w idempotencji, niezależny audyt RLS, odzyskiwania kont,
reklamacji i retencji. Podział 75/20/5 jest funkcją testową, a nie ukończoną
procedurą prawną. Nie zadeklarowano zakończenia całej aplikacji ani wszystkich
360 numerowanych pozycji wcześniejszego pakietu.

## Uruchomienie i dowody

Start: `README.md`. Opis i migracja: `docs/WYSZUKIWANIE_LOKALNE.md`.
Rezerwacje: `docs/REZERWACJE_MAGAZYNU.md`. Używać tylko syntetycznych danych.

Raporty bieżącego pakietu:
`audit_large_local_final_regression.json`, `audit_large_local_final_http.json`,
`audit_large_local_final_soak.json`, `audit_large_local_final_scale.json`,
`audit_large_local_anonymous.json`, `audit_large_local_money.json`,
`audit_large_local_acceptance.json`, `audit_large_local_summary.json`.

Archiwum zawiera pełny kod i lokalną historię Git. Integralność ZIP i zgodność
kodów/testów z przetestowaną czystą kopią są dodatkowo sprawdzane przy pakowaniu.
Szczegóły weryfikacji gotowego ZIP zostaną dopisane do raportu przekazanego
obok archiwum, bez modyfikowania już przetestowanego pliku ZIP.
