# WiejskaPaka — ochrona PIN-u i odpowiedzi zakupowych, 16 października 2026

Commit kodu: `976cb4719c8558873bd8803290d3f9ddb40df16a`.

Odcisk kodu, skryptów i zadeklarowanych zależności: `856439ac6068bd0bcfe436e407fb6dce2b92a56b0dbaf4fc0529d42d53253bd3`.

## Wynik

Zabezpieczono zapisane odpowiedzi zakupów i testowe PIN-y, dodano retencję,
zarządzanie lokalnym kluczem i ochronę autoryzacji ponowień. Dostarczamy pełny
projekt i lokalną historię Git, bez GitHub, publikacji, Actions i usług płatnych.

Dodano **58 zaliczonych przypadków** i jeden natywny test PostgreSQL,
który ma SKIP. To nadal aplikacja demonstracyjna. Nie potwierdzamy gotowości
produkcyjnej ani szacunku 90% ukończenia.

## Wykryte problemy i naprawy

1. **Jawny PIN w bazie idempotencji.** Pełna odpowiedź, w tym PIN, była
   zwykłym JSON-em. Teraz jest szyfrowana AES-256-GCM przez bibliotekę
   `cryptography` 50.0.2. Klucz jest poza bazą. Losowy nonce jest nowy dla
   każdego zapisu; test stabilności sprawdza jego brak powtórzeń pod jednym kluczem.
2. **Nieograniczone odzyskiwanie zapisanych PIN-ów.** Wprowadzono limit
   24 godzin od pierwotnego zakupu. Odczyt po terminie natychmiast pomija PIN;
   zadanie przy starcie i co 30 sekund przepisuje wygasły zapis bez niego.
   Idempotencja nadal zachowuje identyfikator: ponowienie nie tworzy nowego zakupu.
3. **Ryzyko błędnego klucza i podmiany danych.** Odczyt uwierzytelnia
   kupującego, klucz operacji, skrót żądania, wersję i termin/stadium retencji.
   Zmiana danych lub przeniesienie szyfrogramu do innego kupującego daje 409.
   Brak lub zły klucz istniejących zapisów zatrzymuje start bez generowania
   zastępczego klucza. Testy sprawdzają zachowanie bazy bajt w bajt.
4. **Luka czasowa lokalnej autoryzacji ponowień.** Pojedynczy zakup, koszyk
   i uzgodnienie wyniku operacji ponownie sprawdzają sesję i rolę w tej samej
   transakcji. Cofnięta/wygasła sesja lub zmiana roli nie ujawnia cache.
5. **Błędny komunikat UI po braku PIN-u.** Zamiast `undefined` i sugestii
   nowej rezerwacji pokazujemy, że zakup istnieje i należy sprawdzić historię.
   Nieprawidłowa wartość nie jest prezentowana jako prawidłowy PIN.
6. **Dowody testowe nieuwzględniające plików zależności.** Odcisk pełnej
   regresji obejmuje teraz `requirements.txt` i `requirements-lock.txt`.
   Zmiana zadeklarowanej biblioteki unieważnia wynik z wcześniejszego odcisku.

Część zabezpieczeń, w tym ochrona nowego pliku klucza i równoczesnej rotacji,
chroni mechanizm wprowadzony w tej paczce. Nie opisujemy ich jako wcześniej
odtworzonych błędów starej aplikacji. Jeden stary test struktury UI dostosowano
do nowego helpera; zachowanie helpera niezależnie wykonuje Node.

## Klucze, migracja i retencja

- SQLite demo atomowo tworzy własny plik klucza 0600 obok jednorazowej bazy.
  Na POSIX sprawdzamy prawa, właściciela i typ; dowiązania są odrzucane.
- Dla stałej instalacji deweloperskiej zalecamy klucz poza projektem;
  PostgreSQL wymaga jawnego `WP_CHECKOUT_KEY_FILE`. Nie ma klucza w ZIP.
- CLI tworzy i rotuje klucz bez drukowania jego bajtów. Rotacja zachowuje
  stare klucze i wymaga restartu. Osobna blokada POSIX zapobiega utracie kluczy
  przy równoczesnych rotacjach. Limit 16 kluczy nie usuwa automatycznie żadnego.
- Demo i testy nie dziedziczą ścieżki klucza innej instalacji.
- Starszy jawny JSON jest migrowany w jednej transakcji. Wiek PIN-u liczymy
  od starej daty, bez przyznania nowych 24 godzin. Awaria wycofuje migrację.
- Sam status operacji nigdy nie ujawnia PIN-u. Po upływie terminu pozostają
  ID i kwoty zakupu, a PIN znika z odpowiedzi oraz aktualnego zaszyfrowanego cache.
- Ochrona odczytu działa także przed przebiegiem zadania okresowego. Błędy
  retencji są logowane bez danych i ponawiane, niezależnie od wygaszania magazynu.

Nie zmieniono schematu SQL; nowy format dotyczy istniejącej kolumny odpowiedzi.
Przed aktualizacją własnej bazy trzeba wyłączyć starą instancję, zachować kopię
bazy i chroniony klucz. Starszy kod nie czyta nowego formatu; wycofanie wymaga
zgodnego kodu i kopii danych. Szczegóły: `docs/SZYFROWANIE_ODPOWIEDZI_ZAKUPU.md`.

## Faktycznie wykonane testy

| Brama | Wynik |
|---|---|
| Pełna regresja z czystej kopii kodu | 246 modułów; **3128 PASS, 0 FAIL, 16 SKIP** |
| Nowe zaliczone przypadki | 27 magazyn/klucz/szyfrogram, 15 API, 5 rzeczywiste HTTP, 10 UI/CLI/izolacja, 1 odcisk zależności: **58** |
| Długi rzeczywisty HTTP | 1800.41 s, 12648 rund, 108216 żądań, 266633 kontroli: PASS |
| Zakup/historia/PIN/zwrot przez HTTP | 50 liczonych żądań API i 187 kontroli: PASS |
| Dotychczasowa akceptacja HTTP | 4 zadania PASS: loopback, zakup/dostawa/zwrot, wielu sprzedawców, prywatność |
| Prywatne trasy bez sesji | 83/83 zablokowane; 0 wyników niejednoznacznych |
| Rozliczenia | 20 001 kwot, 100 002 kontrole z niezależnym wzorcem Decimal: PASS |
| Składnia i zależności | 108 plików Python, 4 pliki web JS, `pip check`: PASS; cryptography 50.0.2 |
| Natywny PostgreSQL | **NIEZWERYFIKOWANY — 14 SKIP** |
| Chromium | **NIEZWERYFIKOWANY — 2 SKIP** |

SKIP nie jest PASS. Rund i kontroli nie dodajemy do liczby testów pytest.
Testy Node korzystają z kontrolowanego DOM/wykonania JavaScript, bez Chromium.
Testy HTTP uruchamiają prawdziwy Uvicorn i TCP/loopback na jednorazowej SQLite.
Wszystkie konta, adresy i płatności są syntetyczne lub symulowane.

Pięć nowych przypadków HTTP obejmuje pojedynczy zakup i koszyk po restartach,
rotację, wygasły PIN i niezmienną liczbę zamówień; dwa warianty braku/złego
klucza odmawiają startu bez zmiany bazy. Osobny test działającego serwera
sprawdza automatyczny proces retencji w ciągu 36 sekund, bez restartu i bez
jawnego wywołania funkcji czyszczącej. Stary termin symulowano przez poprawne
uwierzytelnione zaszyfrowanie testowej odpowiedzi, nie przez obejście AAD.

Długi test sprawdza m.in. współbieżną idempotencję, ostatnią sztukę, podwójne
anulowanie, wyścig PIN/zwrot, wypłaty testowe, pojedynczą dostawę, unieważnienie
sesji, całkowite grosze, historię zakupu, zgodność magazynu i zapisy bez jawnego
PIN-u. Wcześniejsze diagnostyczne i przerwane raporty nie są dowodem wydania.

Środowisko miało już dostępną bibliotekę cryptography; użyto wersji 50.0.2
w odizolowanym venv i sprawdzono metadane zależności. Nie deklarujemy testu
pobierania paczek z sieci ani instalacji na nowej maszynie.

## Stan projektu i istotne granice

Nie podłączono produkcyjnych płatności, banku, hostingu, domeny ani Neon.
Nie dodano pól telefonu. Dostawa jest płatna raz za przesyłkę, odbiór odbywa
się w punkcie i jest potwierdzany PIN-em, wina dostawcy oznacza pełny zwrot.
Wszystkie kwoty i obliczenia pieniężne pozostają całkowitymi groszami.
Prawa konsumenta pozostają zachowane; PIN ich nie ogranicza.

Plik klucza obok bazy jest rozwiązaniem demonstracyjnym, nie produkcyjnym
magazynem sekretów. Dostęp jednocześnie do klucza i bazy pozwala odszyfrować
zapis. Nie zagwarantowano wymazania starszych zapisów, w tym jawnych PIN-ów sprzed
migracji, z backupów, stron SQLite/WAL lub pamięci. Wymagane są docelowy magazyn kluczy, zasady backupu,
wycofywania kluczy, retencji, odzyskiwania/bezpiecznego przekazywania PIN-u
oraz niezależny audyt. Istniejące hashe sześciocyfrowych PIN-ów w zamówieniach
pozostają częścią dotychczasowego procesu; szyfrowanie cache nie zastępuje
całościowego audytu krótkich kodów i kontroli dostępu. Rotacja jest sprawdzona na POSIX; Windows/ACL wymagają
odrębnej weryfikacji. PIN po 24 godzinach nie jest odzyskiwany przez ten cache.

Natywny PostgreSQL i Chromium pozostają niezbadane z powodu ograniczeń
środowiska. Dodatkowa próba przeglądarki środowiska zakończyła się
`ERR_CONNECTION_REFUSED` dla jednorazowego demo na 127.0.0.1:8765;
nie wykonano przebiegu UI i nie zaliczono tej próby. Dodano natywny przypadek szyfrogramu i związania z kupującym oraz
plik klucza do jego izolowanej konfiguracji, ale nie zaliczono go zastępczo
przez SQLite. Nie ponawiano identycznych prób natywnego uruchomienia z poprzednich sesji.

Pozostałe większe prace: bezpieczna weryfikacja sprzedawcy, opłaty punktów i
roczne rozliczenie kosztów, pełny przegląd RLS/ochrony danych/odzyskiwania kont
oraz procedur konsumenckich. Podział 75/20/5 pozostaje funkcją testową, nie
ukończoną procedurą prawną. Lista: `docs/audits/OGRANICZENIA_I_DALSZE_PRACE.md`.

## Odtworzenie i dowody

Start: `README.md`; klucze, migracja i wycofanie:
`docs/SZYFROWANIE_ODPOWIEDZI_ZAKUPU.md`. Nie przesyłaj własnego klucza do raportu.
Źródło API AES-GCM: https://cryptography.io/en/latest/hazmat/primitives/aead/.

Bieżące wyniki: `audit_vault_final_regression.json`, `audit_vault_final_soak.json`,
`audit_vault_purchase_http.json`, `audit_vault_anonymous.json`,
`audit_vault_money.json`, `audit_vault_acceptance.json`,
`audit_vault_syntax_dependencies.json`, `audit_vault_browser_attempt.json`,
`audit_vault_evidence_integrity.json`, `audit_vault_summary.json`.

Przy pakowaniu weryfikujemy CRC/manifest SHA256, brak bazy i kluczy, zgodność
kodów/testów/zależności z czystą kopią, ponowne wykonanie przypadków z gotowego
ZIP i odtworzenie lokalnej historii Git. Ostateczny wynik tych kontroli zostanie
dopisany do raportu przekazanego obok ZIP, bez zmieniania przetestowanego archiwum.
