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

Nie zaimplementowano jeszcze harmonogramu, szyfrowanego magazynu, retencji,
odtwarzania PostgreSQL/PITR ani procedury odtwarzania po utracie infrastruktury.
Próba nie mierzy RTO/RPO dla rzeczywistych rozmiarów danych, nie sprawdza
awarii zasilania, systemu plików sieciowych ani równoczesnej rotacji kluczy.
Nie potwierdza odtworzenia nieznanych plików zewnętrznych ani zgodności prawnej.
Produkcja pozostaje zablokowana.

Źródła mechanizmu:
https://www.sqlite.org/backup.html
https://www.sqlite.org/wal.html
https://docs.python.org/3.12/library/sqlite3.html#sqlite3.Connection.backup
