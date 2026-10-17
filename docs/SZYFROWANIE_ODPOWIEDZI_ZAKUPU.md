# Szyfrowane odpowiedzi zakupowe i retencja PIN-u

Nowe odpowiedzi idempotentnych zakupów pojedynczych i koszykowych są zapisane
w istniejącej kolumnie `checkout_idempotency.response_json` jako szyfrogram.
Używamy `cryptography` 50.0.2, AES-256-GCM, losowego 12-bajtowego nonce na każdy
zapis oraz danych uwierzytelnianych obejmujących kupującego, klucz operacji,
skrót żądania, wersję formatu, termin i stan retencji. Podmiana tych danych
lub szyfrogramu powoduje odmowę odczytu; nie tworzymy nowego zamówienia.
Dokumentacja biblioteki: https://cryptography.io/en/latest/hazmat/primitives/aead/.

## Klucz poza bazą

W lokalnym SQLite klucz demonstracyjny jest tworzony automatycznie jako
`<ścieżka_bazy>.checkout-key`, jeżeli nie ma jeszcze zaszyfrowanych zapisów.
Plik jest tworzony atomowo, ma uprawnienia 0600, a równoczesne uruchomienia
nie nadpisują klucza. Synchronizujemy plik oraz wpis katalogu po utworzeniu
i rotacji. Na POSIX sprawdzamy właściciela, prawa i typ pliku;
nie akceptujemy dowiązania symbolicznego. Pliki klucza, blokady i tymczasowe
nie mogą znaleźć się w Git ani w archiwum źródeł.

Dla stałej instalacji deweloperskiej zalecamy klucz w prywatnym katalogu poza
projektem. PostgreSQL **wymaga** jawnej konfiguracji `WP_CHECKOUT_KEY_FILE`:

```bash
.venv/bin/python scripts/checkout_keys.py create --path /PRYWATNY_KATALOG/app.checkout-key
export WP_CHECKOUT_KEY_FILE=/PRYWATNY_KATALOG/app.checkout-key
```

Katalog musi istnieć i należeć do operatora. Podana ścieżka jest przykładem;
nie wpisuj klucza do polecenia, kodu, logu ani raportu. CLI pokazuje tylko jego
identyfikator. Demo i testy usuwają odziedziczone `WP_CHECKOUT_KEY_FILE`, żeby
nie otworzyć przypadkiem pliku klucza innej instalacji.

Plik klucza trzeba zachować i chronić niezależnie od kopii bazy. Domyślny
plik obok SQLite jest wygodą demo, a nie produkcyjnym magazynem sekretów.
Kopia samej bazy nie zawiera klucza. Przejęcie jednocześnie bazy i klucza
pozwala odszyfrować dane; niezależny audyt i magazyn kluczy pozostają do wdrożenia.
Na Windows wymagany jest osobny przegląd ACL. Rotacja CLI jest dostępna na POSIX;
nie deklarujemy zaliczenia testów Windows ani gotowości produkcyjnej.

## Restart, utrata i rotacja

Przy starcie wczytujemy klucz i sprawdzamy istniejące szyfrogramy. Brak klucza
istniejących zapisów, zły klucz lub niespójny zapis zatrzymują uruchomienie.
Nie generujemy zastępczego klucza do istniejących szyfrogramów. Błąd odczytu
podczas ponowienia zwraca ogólny 409 i nie uruchamia kolejnego zakupu.

```bash
.venv/bin/python scripts/checkout_keys.py rotate --path /PRYWATNY_KATALOG/app.checkout-key
```

Po rotacji uruchom ponownie aplikację. Stare klucze pozostają w pliku, więc
wcześniejsze odpowiedzi są czytelne; nowe zapisy używają aktywnego klucza.
Stabilny plik blokady chroni równoczesne rotacje przed utratą nowego klucza.
Limit wynosi 16 kluczy; CLI odmawia dalszej rotacji zamiast usuwać stare klucze.
Wycofanie starego klucza wymaga odrębnego planu migracji i kopii zapasowych.

## Retencja i ponowienie

PIN można odzyskać przez ponowienie tej samej operacji maksymalnie przez
24 godziny od pierwotnego zapisu. To limit ujawnienia, nie przedłużenie
rezerwacji magazynowej: nieopłacony zakup nadal wygasa po 30 minutach.
Rezerwacja, status, PIN jednorazowy i zasady potwierdzenia towaru pozostają
niezależnie sprawdzane przez istniejący proces zamówienia.

Po 24 godzinach API nie zwraca PIN-u, także przed fizycznym przepisaniem cache.
Odpowiedź zachowuje ID zamówienia/przesyłki i kwoty oraz zawiera
`pin_available: false` i komunikat, aby nie składać ponownie istniejącego zakupu.
Interfejs nie wyświetla `undefined` i nie sugeruje nowej rezerwacji.
Odczyt statusu operacji nigdy nie ujawnia PIN-u, również przed tym terminem.

Przy starcie oraz co 30 sekund osobny krok utrzymaniowy przepisuje wygasłą
odpowiedź, usuwając pola PIN-u z odszyfrowanej treści i zapisując ponownie
zaszyfrowane dane bez PIN-u. Nie usuwa samego klucza idempotencji: późne
ponowienie nadal nie tworzy drugiego zamówienia ani nie zmienia stanu magazynu.
Awaria retencji jest raportowana ogólnym komunikatem bez sekretów i ponawiana.
Ochrona odczytu działa niezależnie od sukcesu zadania okresowego.

Nie jest to gwarancja wymazania starszych zapisów, w tym jawnych PIN-ów
sprzed migracji, z kopii zapasowych, wcześniejszych stron SQLite/WAL ani pamięci. Trzeba osobno ustalić i wdrożyć
politykę backupów, retencji i zarządzania kluczami przed produkcją.

## Starsze dane i wycofanie wydania

Przy pierwszym uruchomieniu stare odpowiedzi tekstowe są szyfrowane w jednej
transakcji. Termin odzyskania liczymy od starego `created_at`, a nie od migracji;
stary PIN po terminie jest od razu pomijany. Migracja nie potwierdza
historycznej autentyczności danych zapisanych wcześniej bez szyfrowania.
Nie trzeba dodawać tabel ani zmieniać schematu PostgreSQL.

Przed użyciem na własnej bazie wyłącz starszą instancję aplikacji i zachowaj
kopię bazy oraz chroniony plik klucza. Nie mieszaj starych i nowych instancji
zapisujących odpowiedzi w różnych formatach.
Starsza wersja kodu nie rozumie nowego formatu. Wycofanie wydania wymaga
zgodnego kodu i bazy z kopii, nie samej podmiany programu. Demo korzysta wyłącznie
z jednorazowych syntetycznych danych.

## Dostęp i testy

Obie ścieżki zakupu oraz uzgodnienie wyniku operacji sprawdzają sesję i rolę
w transakcji odczytu/zapisu także na SQLite. Cofnięcie sesji, jej wygaśnięcie
lub zmiana roli przed odczytem nie ujawnią zapisanej odpowiedzi.

Testy: `test_checkout_vault.py`, `test_checkout_vault_api.py`,
`test_checkout_vault_http.py`, `test_checkout_vault_ui_cli.py`.
Obejmują rzeczywiste restarty TCP/HTTP, automatyczny proces retencji w działającym
serwerze, rotację, brak/zły klucz i brak nowego zamówienia po upływie retencji.
Testy Node nie są Chromium. Natywny przypadek PostgreSQL jest dostarczony w
`test_postgres_full_api_optin.py`; w tej sesji pozostaje niezweryfikowany.

## Odzyskanie bez klucza operacji

Nowsza paczka dodaje odzyskanie w historii klienta po ponownym podaniu hasła,
powiązania ID zakupów i licznik prób. Wymaga dodatkowej migracji PostgreSQL.
Pełne zasady i ograniczenia: `docs/ODZYSKIWANIE_PIN.md`.
