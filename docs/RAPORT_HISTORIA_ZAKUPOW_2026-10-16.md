# WiejskaPaka — historia zakupu i bezpieczeństwo odczytu, 16 października 2026

Sprawdzony commit kodu: `ee28f711da59bf50825f04c49161e0f4bc3ae629`.

Odcisk źródeł aplikacji i skryptów: `817a3c93f23bf073216804cabcd190e3ac286b82d33b1b3470535222bb6921ae`.

## Wynik

Dodano pierwotne warunki zakupu do nowych zamówień i przesyłek, prywatny
podgląd klienta i rolnika oraz pobieranie JSON. Dane nie zmieniają się po
późniejszej edycji produktu lub punktu odbioru. Pełny projekt pozostaje lokalny:
bez GitHub, publikacji, Actions, płatnych usług i produkcyjnych płatności.

Dodano **57 zaliczonych testów** oraz jeden natywny przypadek PostgreSQL, który
pozostaje pominięty. Wersja jest demonstracyjna; nie deklarujemy 90% ani
ukończenia całej aplikacji. ZIP zawiera cały projekt i historię Git.

## Wykryte problemy i naprawy

1. **Brak utrwalonych pierwotnych warunków.** Po późniejszej edycji katalogu
   lub zakończonego punktu nie można było wiarygodnie odtworzyć pierwotnej
   nazwy, ceny, adresu i godzin. Nowa tabela utrwala je podczas zakupu.
   Nie odtwarzamy starszych zakupów z dzisiejszego katalogu.
2. **Ryzyko częściowego checkoutu przy błędzie archiwizacji.** Zapis jest
   częścią transakcji zamówienia, stanu, rezerwacji i koszyka. Wstrzyknięty błąd
   wycofuje całość. Idempotencja i jednoczesne ponowienia tworzą jeden zapis.
3. **Luka czasowa autoryzacji nowych odczytów SQLite.** Kontrola zależności
   logowania mogła poprzedzać cofnięcie sesji lub zmianę roli przed odczytem.
   Sesja, wygaśnięcie i rola są ponownie sprawdzane w transakcji odczytu.
   Testy obejmują zamówienie, przesyłkę i audyt, po trzy zmiany uprawnień.
   Natywna ścieżka PostgreSQL nadal używa autoryzacji w tej samej transakcji.
4. **Opóźnione odpowiedzi szczegółów i historii finansowej przesyłki.** Dodano
   kontrolę sesji, aktualności żądania i obecności karty. Nowy podgląd oraz
   pobieranie JSON również nie wykonują się po zmianie konta lub odłączeniu karty.

Nie każda dodana kontrola jest osobnym wcześniej odtworzonym błędem starej
wersji. Punkty 2 i część 3 chronią także wprowadzony w tej paczce mechanizm.

## Działanie

- Pojedynczy zakup i koszyk zapisują nazwę/cenę jednostkową, ilość i kwoty,
  realizację, publiczny kod, daty oraz pierwotny termin rezerwacji.
- Odbiór zapisuje nazwę, adres, godziny i opcjonalne współrzędne punktu.
  Dostawa nie duplikuje prywatnego adresu klienta.
- Podgląd otrzymują wyłącznie strony zakupu. Obcy klient/rolnik: 404,
  dostawca/administrator podglądu: 403, brak sesji: 401. Odpowiedzi `no-store`.
- Oryginał jest oddzielony od bieżącego stanu płatności, odbioru i zwrotu.
  Kwoty są całkowitymi groszami. W grupie naliczamy jedną opłatę za dostawę.
- Zwykłe UPDATE, DELETE i zastąpienie istniejącego rekordu SQLite są blokowane.
  PostgreSQL ma jawną migrację i trigger; rzeczywisty test tej ścieżki czeka.
- Niezgodność kwot, stron, daty lub powiązania punktu daje 409. Audyt admina
  rozróżnia niespójność i brak starego zapisu, nie udostępnia nazw/adresów/PIN-ów
  i niczego nie dopisuje.
- Starsza pozycja bez oryginału otrzymuje `original_available: false`.
  Mieszana przesyłka nie dostaje zgadywanej pierwotnej sumy.

## Rzeczywiście wykonane testy

| Brama | Wynik |
|---|---|
| Pełna regresja z czystego archiwum śledzonych źródeł | 242 moduły; **3070 PASS, 0 FAIL, 15 SKIP** |
| Nowe testy zaliczone | 36 API/SQL/autoryzacja, 17 JavaScript, 1 pełny HTTP, 3 restart/współbieżny HTTP: **57** |
| Nowy przepływ rzeczywistego HTTP | 50 liczonych żądań API, 187 kontroli PASS |
| Długotrwały HTTP / SQLite | 1800.42 s; 12716 rund, 109893 żądań, 269514 kontroli PASS |
| Anonimowy dostęp HTTP | 83/83 prywatne trasy zablokowane, 0 wyników niejednoznacznych |
| Dotychczasowa akceptacja HTTP | 4 zadania PASS: loopback, zakup/dostawa/zwrot, wielu sprzedawców, prywatność |
| Rozliczenia finansowe | 20 001 kwot i 100 002 kontrole z niezależnym wzorcem Decimal: PASS |
| Składnia | 106 plików Python i 5 JavaScript: PASS |
| Natywny PostgreSQL | **NIEZWERYFIKOWANY — 13 SKIP** |
| Chromium | **NIEZWERYFIKOWANY — 2 SKIP** |

SKIP nie jest PASS. Żądań i kontroli nie dodajemy do liczby przypadków pytest.
Node wykonuje prawdziwy skrypt UI w kontrolowanym DOM, bez uruchamiania
Chromium. HTTP uruchamia rzeczywisty Uvicorn/TCP na loopback z jednorazową
SQLite, danymi syntetycznymi i symulowanymi płatnościami.

Nowe testy sprawdzają atomowość, idempotencję, zakaz modyfikacji SQL, dostęp,
brak PIN-u/adresu/telefonu w eksporcie, stare dane bez oryginału, punkt bez
współrzędnych, wygaśnięcie rezerwacji, późniejszą zmianę katalogu, odbiór PIN-em,
pełny zwrot i wykrywanie niespójnych danych. Test restartu trzykrotnie uruchamia
serwer na tej samej syntetycznej bazie, sprawdza zachowanie oryginałów,
cofnięcia sesji oraz triggerów. Dwa testy wyścigów wykonują po osiem zakupów
z równoczesnymi odczytami i zwrotem; odczyt nie może mieszać stanów transakcji.

Długi test obejmuje konkurencyjnych kupujących, idempotencję, podwójne anulowanie,
wyścig PIN/zwrot, pojedynczą dostawę, wypłaty symulowane, cofnięcie sesji,
ścisłe grosze, prywatne podglądy i cykliczną kontrolę wszystkich oryginałów.
Wcześniejsze, przerwane w trakcie poprawiania kodu raporty nie są dowodem wydania.

## Stan i ograniczenia

Nie podłączono produkcyjnych płatności, banku, domeny, hostingu ani Neon.
Nie dodano pól telefonów. Dostawa na adres jest płatna, odbiór jest w punkcie,
PIN potwierdza odbiór. Wina dostawcy daje pełny zwrot, również dostawy.
Prawa konsumenta pozostają zachowane; PIN nie ogranicza roszczeń.

Archiwalny zapis testowy nie jest fakturą, dowodem prawdziwej płatności ani
podpisanym dokumentem. Nie kopiujemy danych urzędowych ani bankowych.
Trigger nie chroni przed administratorem bazy usuwającym zabezpieczenia.
Polityka retencji, kontrolowane usuwanie/anonimizacja i przegląd prawny
wymagają osobnego opracowania przed produkcją. Zwykłe kasowanie jest blokowane.

Natywny PostgreSQL wymaga innego działającego środowiska: ta sesja nie uzyskała
serwera z odpowiednią izolacją/uprawnieniami. Chromium również pozostaje
zablokowane ograniczeniami środowiska. Nie uznano SQLite i Node za ich
zamienniki. Nie ponawiano identycznych nieskutecznych prób.

Pozostały m.in. bezpieczna weryfikacja sprzedawcy, opłaty punktów i roczne
rozliczenia kosztów, ochrona i retencja testowego PIN-u w zapisach idempotencji,
niezależny audyt RLS/ochrony danych/odzyskiwania kont i procedur konsumenckich.
Podział 75/20/5 pozostaje testową funkcją, nie ukończoną procedurą prawną.
Pełna lista: `docs/audits/OGRANICZENIA_I_DALSZE_PRACE.md`.

## Kod i odtworzenie

Pełny kod jest w przekazanym ZIP. Start: `README.md`. Szczegóły modelu i migracji:
`docs/HISTORIA_ZAKUPOW.md`. Natywne testy: `docs/POSTGRESQL_TESTY_LOKALNE.md`.

Bieżące dowody: `audit_purchase_records_final_regression.json`,
`audit_purchase_records_final_http.json`, `audit_purchase_records_final_soak.json`,
`audit_purchase_records_anonymous.json`, `audit_purchase_records_money.json`,
`audit_purchase_records_acceptance.json`, `audit_purchase_records_syntax.json`
i `audit_purchase_records_summary.json`.

Integralność ZIP, manifest plików, zgodność kodu z czystą przetestowaną kopią,
odtworzenie historii Git oraz ponowne testy nowej funkcji po rozpakowaniu są
sprawdzane przy pakowaniu. Ostateczne wyniki są dopisywane do raportu obok ZIP,
bez przepisywania zawartości przetestowanego archiwum.
