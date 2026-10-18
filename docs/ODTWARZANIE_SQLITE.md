# Próba odtwarzania SQLite — wyłącznie środowisko testowe

`tests/test_sqlite_recovery_rehearsal.py` tworzy syntetyczne konta i zakupy
w jednorazowym katalogu. Nie przyjmuje ścieżki do bazy użytkownika i nie
łączy się z PostgreSQL. Uruchomienie w odizolowanym środowisku projektu:

```bash
python scripts/run_tests_per_file.py test_sqlite_recovery_rehearsal.py --report recovery.json
```

## Co sprawdza próba

Kopię tworzy SQLite Online Backup API (`Connection.backup`), z osobnego
połączenia tylko do odczytu, do nowego pliku. Próba utrzymuje aktywne WAL
i niezakończoną transakcję piszącą. Odtworzenie obejmuje zatwierdzony zakup,
pomija niezapisany nowy cennik i przechodzi `integrity_check` oraz
`foreign_key_check`. Nie jest to kopiowanie samego pliku `.sqlite3` w trakcie
pracy bazy.

Drugi proces aplikacji uruchamia odtworzoną kopię z właściwym kluczem.
Kontrole obejmują oryginalny zapis zakupu, historię symulowanej płatności,
pojedynczą opłatę za przesyłkę (501 groszy dla dwóch produktów), ponowienie
tej samej operacji bez duplikatu oraz blokady SQL zabraniające nadpisania
i usunięcia warunków zakupu. Zaszyfrowany cache zachowuje tożsamość zakupu.
Kopia uruchamiana bez klucza lub z obcym kluczem odmawia startu i nie tworzy
zastępczego klucza. Kontrola porównuje też niezmienność bazy i klucza źródła.

Osobny przypadek potwierdza ograniczenie punktu odtworzenia: wylogowanie
wykonane po kopii nie istnieje w odtworzonej bazie. Unieważnienie sesji
wyłącznie w jednorazowej kopii przywraca odmowę dostępu i zachowuje zakupy
oraz spójność płatności. Test nie unieważnia sesji w źródle ani bazie użytkownika.

Klucz kopiowany w próbie należy wyłącznie do syntetycznej bazy. Nie jest
drukowany ani dołączany do raportu. Uprawnienia 0600 użyte w próbie nie
potwierdzają poprawności Windows ACL.

## Wymagania przyszłej procedury operacyjnej

To test mechanizmu, a nie gotowa usługa backupów. Przed użyciem na rzeczywistych
danych potrzebna jest sprawdzona procedura z następującymi etapami:

1. Zatrzymać ruch i zadania zapisujące; wstrzymać rotację kluczy. Ustalić
   punkt odtworzenia, wersję aplikacji, schemat i dopuszczalną utratę zmian.
2. Zachować spójną kopię bazy i właściwy komplet kluczy. Baza zawiera również
   dane nieobjęte szyfrowaniem cache, więc wymaga szyfrowania całej kopii.
   Klucze przechowywać w osobno zabezpieczonym magazynie. Nie umieszczać
   bazy ani kluczy w Git, logach lub artefaktach CI.
3. Odtwarzać do nowego, izolowanego katalogu, z wyłączonymi zewnętrznymi
   integracjami i ruchem użytkowników. Nie nadpisywać źródłowej bazy ani
   pierścienia kluczy. Zachować możliwość porównania i wycofania operacji.
4. Sprawdzić integralność, klucze obce, schemat, liczniki zakupów, płatności
   i spójność zdarzeń. Sama poprawność pliku SQLite nie oznacza poprawności
   biznesowej. Zmierzyć rzeczywisty czas odtworzenia i utracony okres zmian.
5. Rozstrzygnąć zmiany bezpieczeństwa wykonane po punkcie kopii. Przywrócenie
   bazy cofa również wylogowania, zmiany hasła, blokady i cofnięcia uprawnień.
   Unieważnienie odziedziczonych sesji przed przywróceniem ruchu jest konieczne,
   ale samo nie rozwiązuje przywrócenia starszych haseł lub uprawnień.
6. Uzgodnić stan z zewnętrznymi systemami przed uruchomieniem zadań i ruchu.
   Gdy kiedyś zostanie dodany operator płatności, przywrócenie lokalnego stanu
   nie może oznaczać ponownego obciążenia ani ponownego zwrotu.

Nie zaimplementowano jeszcze harmonogramu, zdalnego magazynu, retencji,
odtwarzania PostgreSQL/PITR ani procedury odtwarzania po utracie infrastruktury.
Próba nie mierzy RTO/RPO dla rzeczywistych rozmiarów danych, nie sprawdza
awarii zasilania, systemu plików sieciowych ani równoczesnej rotacji kluczy.
Nie potwierdza odtworzenia nieznanych plików zewnętrznych ani zgodności prawnej.
Produkcja pozostaje zablokowana.

Źródła mechanizmu:
https://www.sqlite.org/backup.html
https://www.sqlite.org/wal.html
https://docs.python.org/3.12/library/sqlite3.html#sqlite3.Connection.backup

## Narzędzie lokalne: kopia i izolowane odtworzenie

`scripts/sqlite_snapshot.py` działa wyłącznie na jawnie wskazanym lokalnym
pliku SQLite. Nie odczytuje `DATABASE_URL`, nie uruchamia aplikacji, nie
nadpisuje istniejącego celu i nie tworzy zastępczego klucza. Przykład dla
syntetycznej bazy demonstracyjnej (katalog nadrzędny celu musi istnieć):

```bash
python scripts/sqlite_snapshot.py backup --source /tmp/demo.sqlite3 --key-file /tmp/demo.sqlite3.checkout-key --destination /tmp/demo-kopia
python scripts/sqlite_snapshot.py restore --source /tmp/demo-kopia/database.sqlite3 --key-file /tmp/demo-kopia/database.sqlite3.checkout-key --destination /tmp/demo-odtworzone
```

Obie operacje wykonują Online Backup API oraz kontrolę integralności SQLite,
kluczy obcych, odczytu wszystkich zaszyfrowanych odpowiedzi zakupowych i audyt
symulacji płatności. `restore` dodatkowo usuwa wszystkie odziedziczone sesje i, jeśli istnieje
tabela resetu hasła, wszystkie odziedziczone linki resetujące.
Wynik zawiera tylko liczniki, bez PIN-ów, danych kont i ścieżek. Błąd usuwa
nowo utworzony katalog częściowej kopii. Istniejący cel pozostaje nietknięty.
Limit kopiowania wynosi domyślnie 30 sekund (`--timeout`).

Cel zawiera `database.sqlite3` i właściwy `database.sqlite3.checkout-key`.
Na POSIX katalog otrzymuje uprawnienia 0700, pliki 0600. Przed operacją należy
wstrzymać rotację kluczy i użyć zaufanego katalogu poza katalogiem serwowanym
przez HTTP. Zmiana pierścienia podczas kopiowania powoduje odmowę.

**Cała kopia nie jest szyfrowana, a klucz znajduje się obok bazy.** To pomoc
przy lokalnym odbiorze wersji testowej, nie magazyn kopii produkcyjnych.
Nie umieszczać wyniku w Git, CI ani współdzielonych katalogach. Szyfrowanie
magazynu, oddzielne przechowywanie kluczy, harmonogram, retencja, Windows ACL
i PostgreSQL nadal wymagają osobnego wdrożenia. Usunięcie sesji nie rozwiązuje
cofnięcia haseł i uprawnień do stanu z kopii. Kontrola płatności nie zastępuje
uzgodnienia z przyszłym operatorem. Narzędzie nie włącza ruchu po odtworzeniu.

## Szyfrowany plik kopii lokalnej (wersja testowa)

`scripts/encrypted_sqlite_snapshot.py` dodaje osobny kontener AES-256-GCM.
Obejmuje całą kopię SQLite i jej pierścień kluczy zakupowych. Niezależny losowy
klucz kopii musi znajdować się poza katalogiem archiwum; program odrzuca
wspólne klucze kopii i bazy. Nie tworzy klucza zastępczego podczas odtwarzania.
Poniższy przykład wymaga istniejących, zaufanych prywatnych katalogów
`/tmp/wp-klucze` i `/tmp/wp-kopie` oraz syntetycznej bazy demonstracyjnej:

```bash
python scripts/encrypted_sqlite_snapshot.py init-key --backup-key /tmp/wp-klucze/demo.backup-key
python scripts/encrypted_sqlite_snapshot.py backup --source /tmp/demo.sqlite3 --checkout-key /tmp/demo.sqlite3.checkout-key --backup-key /tmp/wp-klucze/demo.backup-key --destination /tmp/wp-kopie/demo.wpbackup
python scripts/encrypted_sqlite_snapshot.py restore --archive /tmp/wp-kopie/demo.wpbackup --backup-key /tmp/wp-klucze/demo.backup-key --destination /tmp/demo-odtworzone-szyfrowane
```

Odtwarzanie najpierw uwierzytelnia cały kontener, następnie sprawdza bazę,
zaszyfrowane rekordy zakupów i audyt płatności oraz unieważnia sesje i linki
resetowania hasła. Nie nadpisuje istniejącego celu. Nagłówek, identyfikator
klucza, nonce i treść są objęte uwierzytelnieniem. Publikacja kompletnego
archiwum jest atomowa i odmawia zastąpienia istniejącego pliku.

Limit bazy wynosi 64 MiB, pierścienia 16 KiB. Operacja wymaga pamięci na całą
zawartość i jej kopie robocze. Podczas obu operacji powstają prywatne jawne
pliki tymczasowe, usuwane przy zwykłym zakończeniu, również po błędzie.
Nie zapewnia to bezpiecznego wymazania ani sprzątania po awarii zasilania.
Na POSIX nowe pliki mają 0600; Windows wymaga osobnego zabezpieczenia ACL.
Należy wstrzymać rotację kluczy na czas operacji. Oddzielny katalog nie oznacza
oddzielnego nośnika ani ochrony przed przejęciem konta operatora.

Narzędzie obsługuje lokalne kopie testowe. Harmonogram, retencja, magazyn
zdalny, odtwarzanie PostgreSQL i procedury produkcyjne nadal wymagają wdrożenia.
Utrata klucza uniemożliwia odtworzenie. Kluczy, archiwów i jawnych plików
roboczych nie wolno dodawać do repozytorium lub artefaktów CI.
Opis narzędzia `sqlite_snapshot.py` powyżej nadal dotyczy kopii jawnej.

Dokumentacja zastosowanego AEAD:
https://cryptography.io/en/latest/hazmat/primitives/aead/#cryptography.hazmat.primitives.ciphers.aead.AESGCM
