# Paczka #60 — osobne widoki, oferty i punkty

Repozytorium: `Orgian1/WiejskaPaka`.
Gałąź: `codex/issue-60-separate-views-20261113`.
Baza: `codex/issue-59-pre-vps-20261113`, SHA
`35c4c0aa0c48860e4ee1b19956acb629aab47c7c`.

## Jedno polecenie PowerShell w istniejącym folderze testowym

Zakłada istniejącą `.venv` z zależnościami poprzedniego demo. Paczka nie dodaje
zależności. Zamknij poprzedni lokalny serwer Ctrl+C. W folderze repozytorium
wklej całą poniższą linię:

```powershell
& { if (git status --porcelain) { throw 'Zachowaj lokalne zmiany przed aktualizacja.' }; git fetch origin codex/issue-60-separate-views-20261113; if ($LASTEXITCODE -ne 0) { throw 'Blad pobierania' }; git switch --detach FETCH_HEAD; if ($LASTEXITCODE -ne 0) { throw 'Blad zmiany wersji' }; & .\.venv\Scripts\python.exe scripts/run_phone_demo.py --full-demo --public-geocoder photon }
```

Polecenie przerywa się przy lokalnych zmianach albo błędzie Git. Nie wykonuje
resetu ani czyszczenia plików. Odłączenie HEAD jest celowe: uruchamiasz dokładnie
pobrany commit demo, bez zmiany własnych lokalnych gałęzi. Pełny SHA porównaj
z końcową odpowiedzią Codex w rozmowie. Raport w repozytorium oznacza osobno
commit kodu poddany testom; następujący po nim commit dokumentacji nie zmienia aplikacji. Nie używaj tego polecenia w działającym katalogu VPS.

Przy kolejnym uruchomieniu tej samej wersji wystarczy:

```powershell
.\.venv\Scripts\python.exe scripts/run_phone_demo.py --full-demo --public-geocoder photon
```

Gdy `.venv` nie istnieje, najpierw utwórz ją przez `py -3.12 -m venv .venv`
i zainstaluj `requirements-lock.txt`. Hasła fikcyjnych kont są pokazywane lokalnie
przez launcher; nie wklejaj ich do publicznego issue/PR. Każde demo ma osobną
bazę i konta. Dotychczasowa baza demo nie jest nadpisywana.

## Lista odbiorowa na komputerze i telefonie

1. Strona startowa pokazuje katalog, a pozostałe obszary otwierasz górną nawigacją.
   Przejdź klawiaturą Tab/Enter do Konto, Koszyk, Ulubione, Zamówienia,
   Portfel, Kontakt i zakładek sprzedawcy. Sprawdź wstecz/przód.
2. W katalogu wpisz nazwę, wybierz kategorię, podkategorię, dostępność i sposób
   realizacji. Produkty mają strony po maksymalnie 20 i numerowane przyciski.
   Przejście do innego widoku i powrót zachowuje filtry/stronę; adres `#products?...`
   zachowuje publiczne filtry również po odświeżeniu. Współrzędne nie trafiają
   do URL ani pamięci przeglądarki; lokalizację zapamiętaj jawnie na koncie.
3. Odśwież prywatny URL, np. `#cart`. Tokeny nadal są wyłącznie w pamięci,
   więc po odświeżeniu trzeba zalogować się ponownie. Login pokazuje formularz,
   a po zalogowaniu ten prywatny widok. Konta nie mogą odczytać cudzych danych.
4. Sprawdź serduszka, czerwone liczniki, koszyk, jedną opłatę dostawy na przesyłkę,
   płatność wyłącznie testową, portfel i jednorazowy PIN. Rozwinięcie produktu
   nadal pojawia się pod odpowiednim rzędem.
5. Sprzedawca → Moje ogłoszenia: zmień cenę i wolny stan; sprawdź potwierdzenie
   i wynik w katalogu klienta. Otwórz szczegółową edycję opisu/kategorii;
   zdjęcia zmienisz przez odsyłacz do ustawień zdjęć. Wycofaj i wznów ofertę.
   Wycofanie nie usuwa towaru ani historii. Anulowanie starszego zamówienia
   przywraca stan, lecz samo nie wznawia wycofanej oferty.
6. Otwórz tę samą ofertę na drugim urządzeniu, kup produkt jako klient,
   następnie spróbuj zapisać stary stan jako sprzedawca. Powinien pojawić się
   konflikt wymagający odświeżenia. Stan oznacza towar wolny do nowych zakupów,
   bez ilości już zarezerwowanej. Cena/jednostka istniejącego zakupu pozostaje.
7. Punkty odbioru: dodaj punkt z mapy/adresu/GPS, edytuj nazwę, adres, godziny,
   daty obecności i aktywność. Współrzędne nie mają widocznych pól edycji.
   Przy niedostępnym Photon pozostaje lokalna mapa i ręczny wybór jej środka.
   Zmiany adresu wymagają ponownego wskazania położenia.
8. Spróbuj usunąć punkt z aktywnym zamówieniem: oczekiwany jest komunikat odmowy.
   Wyłączenie nowych zakupów jest możliwe. Po zakończeniu zamówień można
   potwierdzić usunięcie z aktywnych; historia, PIN-y, opłaty i wykorzystanie
   promocji pozostają. Nie jest to kasowanie rekordów bazy.
9. Sprawdź kolejność punktów i wieloczęściową nawigację sprzedawcy, dostawy,
   panel dostawcy oraz administrację. Kontakt jest jednym osobnym widokiem,
   domyślnie zwiniętym; zgłoszenie problemu przy zakupie otwiera go bez duplikatu.

Telefon musi mieć dostęp do tego samego demo przez zaufany HTTPS, aby GPS działał.
Instrukcja certyfikatu i prywatnej sieci Wi-Fi:
[odbiór właściciela](ODBIOR_WLASCICIELA_2026-11-13.md).
Nie wystawiaj niechronionego demo/symulowanych płatności do publicznego Internetu.

Photon nadal jest opcjonalną usługą publiczną. Diagnostyka na Windows:
` .\.venv\Scripts\python.exe -m scripts.check_photon_demo `.
Nie omijaj TLS. Ograniczenia sieci chmurowej i e-maila z paczki #59 pozostają:
[diagnoza Photon](RAPORT_ISSUE_59_2026-11-13.md).

## Bezpieczna aktualizacja VPS — tylko plan

**Żadnego wdrożenia nie wykonywano.** Zastosuj
[procedurę kopii, odtworzenia i rollbacku](AKTUALIZACJA_VPS_ODBIOR_2026-11-13.md)
oraz [listę przygotowania #59](ISSUE_59_ODBIOR_I_VPS_2026-11-13.md).
Dla tej paczki operator musi dodatkowo:

1. Zabezpieczyć bazę (SQLite backup API/WAL lub zgodny `pg_dump`), zdjęcia,
   konfigurację i klucze, stare wydanie/venv i kolejki. Odtworzyć kopię
   w izolacji i sprawdzić odszyfrowanie historycznych zakupów.
2. Utworzyć osobny katalog kandydata z zatwierdzonym SHA tej gałęzi, zachowując
   działający podgląd. Bez `git reset`, czyszczenia czy nadpisywania katalogu usługi.
3. Na kopii istniejącej bazy PostgreSQL zastosować wyłącznie brakujące,
   zweryfikowane migracje. Nowa, **46. pozycja manifestu** to
   `database/optional_product_listing_states.sql`: tworzy tabelę dostępności,
   nie przepisuje produktów, cen, zdjęć, zapasów ani zamówień. Brak wpisu oznacza
   dotychczasową aktywną ofertę. Migracja jest idempotentna. SQLite tworzy tę
   tabelę addytywnie przy uruchomieniu; przedtem również wymaga kopii.
   Dla istniejącej roli aplikacji PostgreSQL operator sprawdza minimalne
   uprawnienia SELECT/INSERT/UPDATE nowej tabeli; nie nadaje superuser ani
   uprawnień do cudzych schematów. Samo utworzenie tabeli przez właściciela
   migracji nie gwarantuje dostępu dotychczasowej roli aplikacji.
4. Wykonać preflight i powyższe testy na osobnym, chronionym HTTPS i bazie kopii.
   Zachować `WP_REAL_PAYMENTS=0`, brak produkcyjnego PayU, odłączone workery
   rzeczywistej poczty. Sprawdzić role, konta, grosze, PIN, rezerwacje i konflikty.
5. Dopiero po osobnej decyzji właściciela uzgodnić przełączenie usług. Poprzedni
   podgląd pozostaje dostępny. Po przełączeniu powtórzyć testy na komputerze
   i fizycznym telefonie oraz sprawdzić błędy i liczniki.
6. Przy rollbacku zatrzymać nowe zapisy/workery, zabezpieczyć stan po awarii,
   wrócić do starego kodu/venv/konfiguracji i sprawdzić zgodność schematu.
   Nie usuwać tabeli dostępności: stara wersja jej nie zna i mogłaby pokazywać
   wycofane oferty, dlatego bezpieczny powrót wymaga zamknięcia nowych zakupów
   do oceny operatora. Nie odtwarzać starej bazy ponad nowymi zamówieniami.
   Zachować uzgodnienie sald i kwarantannę odtworzonych sesji/kolejek.
