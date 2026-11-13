# Paczka #59 — odbiór demo i plan aktualizacji

Repozytorium `Orgian1/WiejskaPaka`, gałąź `codex/issue-59-pre-vps-20261113`.
Baza: `codex/product-categories-filters-20261113`, commit
`6af63fa5efc8d19be8f5c53695bb6195bb8b9139`.
Zgłoszenie: https://github.com/Orgian1/WiejskaPaka/issues/59.

## Uruchomienie najnowszego demo na Windows

Pobierz do nowego katalogu, bez nadpisywania dotychczasowej wersji:

```powershell
git clone --single-branch --branch codex/issue-59-pre-vps-20261113 https://github.com/Orgian1/WiejskaPaka.git WiejskaPaka-issue59
cd WiejskaPaka-issue59
git rev-parse HEAD
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe scripts/run_phone_demo.py --full-demo --public-geocoder photon
```

Porównaj pełny SHA z raportem. Launcher tworzy nowe fikcyjne konta i nową bazę;
nie przenosi danych z poprzedniego uruchomienia. Hasła z terminala zachowaj
prywatnie; nie publikuj terminala ani pliku kont w zgłoszeniu. Ctrl+C kończy demo.
Na Linux/macOS odpowiednikiem interpretera jest `.venv/bin/python`.

Telefon: użyj tego samego działającego demo i kont, z opcjonalnym `--host`
prywatnego adresu komputera oraz `--ssl-certfile` i `--ssl-keyfile`, zgodnie
z [instrukcją Wi-Fi i HTTPS](ODBIOR_WLASCICIELA_2026-11-13.md).
GPS na telefonie wymaga zaufanego HTTPS i zgody. Nie omijaj błędów certyfikatu.
Dla podglądu na VPS operator przygotowuje uwierzytelniony dostęp HTTPS;
nie wystawia surowego portu z symulowanymi płatnościami publicznie.

## Co sprawdzić po uruchomieniu

1. Bez logowania widać logowanie i odzyskiwanie hasła, gdy jest włączone.
   Po zalogowaniu klienta i sprzedawcy oba formularze znikają. Zmiana własnego
   hasła jest w „Bezpieczeństwo konta i potwierdzenie e-maila”. Po zmianie
   hasła sesje są unieważniane; zaloguj się ponownie nowym hasłem.
2. Klient nie ma kontrolek wysyłania zdjęć. Zdjęcia produktów pozostają widoczne;
   sprzedawca nadal dodaje zdjęcia oferty i korzysta z własnego panelu zdjęć.
3. Zapisz ofertę w ulubionych: czerwona plakietka pokazuje liczbę unikalnych
   produktów. Dodaj do koszyka dwie sztuki jednego produktu: plakietka pokazuje
   **jedną pozycję**. Zmiana ilości nie zwiększa liczby pozycji. Usuwanie ostatniej
   pozycji/oferty ukrywa plakietkę. Po ponownym logowaniu liczniki odtwarzają się.
   Odświeżenie danych z drugiego urządzenia jest pobierane przy powrocie do okna
   i okresowo co 30 sekund; lokalne operacje aktualizują liczniki na bieżąco.
4. Na dole jest jeden „Zgłoś problem / Kontakt”, domyślnie zamknięty i bez
   widocznych pól. Kliknięcie rozwija, kolejne zwija i zachowuje szkic. Wylogowanie
   lub zmiana konta zamyka sekcję i usuwa szkic. Zachowanie jest wspólne dla klienta
   i sprzedawcy. Zgłoszenie problemu przy zakupie otwiera formularz w tej sekcji.
   Sprawdź zapis, odpowiedź sprzedawcy i obsługę administratora.
5. „Blisko mnie” używa wybranego/zapisanego miejsca. Bez niego prosi o GPS po
   kliknięciu użytkownika. Sprawdź zgodę, odmowę, brak sygnału, timeout i próbę
   w niezabezpieczonym HTTP. Przy braku GPS pozostaje wybór adresu.
6. Sprawdź Photon: `Wroclaw`, `Wrocław`, `Łódź`, ulicę `Świdnicka 1` z miastem,
   kod `50-001`, brak wyników i brak sieci. Wynik trzeba jawnie wybrać;
   wyszukiwarka nie ustawia pierwszego trafienia automatycznie.
7. Sprzedawca: licznik „Zamówienia” obejmuje tylko aktualne pozycje, bez historii.
   Rozwiń punkt, przejdź na następną stronę 20 zamówień, sprawdź numery,
   produkty, ilości, statusy i PIN. Dostawy na adres mają osobną zwijaną sekcję
   oraz przejście do istniejących terminów/zatwierdzania. Panel dodatkowych
   danych ładuje początkowo po 20 przesyłek/zamówień, z przyciskiem kolejnej partii.
8. Powtórz katalog, kategorie/filtry, ulubione, koszyk, testową płatność, odbiór
   jednym PIN-em, ponowne użycie PIN-u, dostawę i testowy portfel. Sprawdź jedną
   opłatę za przesyłkę, kwoty w groszach i prowizje 5%/0%.

Ogólny formularz e-mail nadal nie wysyła wiadomości bez skonfigurowanej usługi;
przycisk jest wtedy wyłączony i komunikat mówi to wprost. **Zgłoszenia zakupowe
zapisują się w bazie i działają niezależnie od SMTP**. Paczka nie włącza poczty
produkcyjnej. Lokalny reset hasła korzysta z testowej skrzynki pokazanej przez
launcher. Późniejszy test rzeczywistych wiadomości wymaga osobnej konfiguracji
operatora i wyłącznie skrzynek testowych, bez wysyłania do historycznych odbiorców.

## Diagnostyka Photon z tego samego Windows/Pythona

W drugim terminalu, w katalogu repozytorium:

```powershell
.\.venv\Scripts\python.exe -m scripts.check_photon_demo --report "$env:TEMP\wiejskapaka-photon-59.json"
```

Wybierz nową nazwę raportu, jeżeli plik już istnieje. Skrypt wykonuje cztery
zapytania o stałe publiczne `Wroclaw`, z odstępami, i porównuje:

- minimalne zapytanie urllib/systemowy TLS,
- minimalne zapytanie HTTPX/domyślny magazyn zaufania,
- poprzednie parametry aplikacji z `lang=pl`,
- poprawione parametry z `lang=default` i systemowymi certyfikatami.

HTTP 200 jest dodatkowo sprawdzane jako poprawna odpowiedź geokodera.
Raport rozróżnia odrzucony język, opcjonalne pola null, różnicę magazynu
certyfikatów, blokadę proxy i brak potwierdzenia dostępu. Nie zawiera pełnych
adresów z odpowiedzi, haseł, tokenów ani wartości proxy. Nie wyłącza TLS
ani nie zmienia ustawień komputera. Nie uruchamiaj go w pętli.

Samo HTTP 200 dla zapytania minimalnego nie rozstrzyga, dlaczego wcześniejsze
zapytanie aplikacji zawiodło. Potwierdzone błędy kontraktu i ograniczenia
weryfikacji Windows opisuje [raport paczki](RAPORT_ISSUE_59_2026-11-13.md).

## Plan aktualizacji VPS — jeszcze niewykonany

1. Operator zapisuje rzeczywisty SHA, stan usług, konfigurację/porty i flagi,
   w tym workery. Zachowuje obecny podgląd. Nie robi `pull`, `reset --hard`
   ani checkout w działającym katalogu z niezabezpieczonymi zmianami.
2. W uzgodnionym oknie robi spójną, szyfrowaną kopię bazy, zdjęć, kluczy sejfu
   i kolejek, konfiguracji oraz starego kodu/venv. SQLite wymaga backup API/WAL,
   PostgreSQL zgodnego pg_dump. **Odtwarza kopię w osobnej izolowanej bazie**
   i sprawdza dostęp do zaszyfrowanych zakupów, salda i spójność danych.
3. Tworzy nowy katalog wydania, przypina pełny zatwierdzony SHA nowej gałęzi
   i instaluje `requirements-lock.txt` w osobnym venv. Ta paczka nie dodaje SQL;
   bazą jest poprzedni manifest **45 migracji**, w tym kategorii. Porównuje
   faktyczny schemat VPS i historię migracji; na starszej bazie stosuje tylko
   brakujące, wcześniej sprawdzone zmiany na kopii. Nie uruchamia bootstrapu
   pustej bazy na istniejących danych. Nowy endpoint liczników używa dotychczasowych
   tabel ulubionych, koszyka i zamówień oraz istniejących uprawnień.
4. Uruchamia kandydata obok istniejącego podglądu, na osobnej bazie i prywatnym
   porcie. Korzysta z `deploy/preview/preview.env.example` oraz guardów
   `backend.test_server_launcher`: `WP_ENV=test`, `WP_REAL_PAYMENTS=0`,
   bez konfiguracji PayU i bez automatycznego uruchamiania workerów SMTP.
   Symulacje włącza tylko w zamkniętym demo. Wszystkie wymagane tabele dla
   aktywnych flag muszą przejść preflight.
5. Na kandydacie wykonuje listę powyżej na komputerze i telefonie przez HTTPS.
   Włącza Photon tylko jawnie i sprawdza ruch HTTPS do `photon.komoot.io`.
   Nie pomija weryfikacji certyfikatów przy proxy. Ogólny e-mail i workery
   pozostają wyłączone do osobnej, świadomej konfiguracji testowej.
6. Dopiero po odrębnej decyzji właściciela przełącza uzgodnioną usługę/wskaźnik
   wydania. Zaraz sprawdza health, logowanie, GPS, koszyk, zamówienia, PIN-y,
   portfel i błędy. Zachowuje stary podgląd i venv jako punkt powrotu.
7. Wycofanie: zatrzymuje nowe zapisy/workery, zabezpiecza stan po awarii,
   przywraca poprzedni kod/venv/konfigurację i sprawdza zgodność schematu.
   **Nie odtwarza automatycznie starej bazy ponad nowymi zamówieniami.**
   Nie usuwa blokad idempotencji, decyzji/warunków portfela ani metadanych kategorii.
   Gdy konieczne jest odtworzenie, rozlicza okres zmiany i poddaje sesje oraz
   kolejki z kopii kwarantannie, aby uniknąć ponownych operacji i wysyłek.

Szczegóły kopii, migracji i rollbacku:
[bezpieczna procedura VPS](AKTUALIZACJA_VPS_ODBIOR_2026-11-13.md).
Żadnego z kroków wdrożeniowych nie wykonywano w tym zadaniu na działającym VPS.
