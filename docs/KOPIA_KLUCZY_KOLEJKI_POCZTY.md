# Szyfrowana kopia kluczy poczty — etap testowy

Narzędzie `python -m scripts.mail_queue_key_backup` tworzy osobną szyfrowaną
kopię całego wersjonowanego pęku kluczy poczty i odtwarza ją do nowego pliku.
Nie tworzy kopii bazy, nie podmienia aktywnych kluczy aplikacji, nie zmienia
konfiguracji, nie uruchamia pracownika ani SMTP. Odzyskanie kluczy nie jest
zgodą na uruchomienie historycznych zadań z odtworzonej bazy.

## Pliki i rozdzielenie

Operacje wymagają POSIX, bezwzględnych ścieżek poza projektem i prywatnych
katalogów należących do bieżącego użytkownika (bez dostępu grupy i innych).
Dowiązania w ścieżce są odrzucane. Istniejące klucze i archiwa wymagają
prywatnych uprawnień pliku. Nowe pliki powstają z prawami 0600.
Istniejący cel nie jest nadpisywany, także przy błędzie lub dowiązaniu.

Klucz szyfrujący kopię musi znajdować się poza katalogiem archiwum i nie może
współdzielić żadnego materiału kryptograficznego z pękiem kluczy poczty.
Odtworzony pęk również zapisuje się poza katalogiem archiwum. To logiczne
rozdzielenie katalogów; niezależny nośnik, host i prawa operatora pozostają
częścią procedury wdrożeniowej.

## Operacje

Poniższe placeholdery trzeba zastąpić prywatnymi bezwzględnymi ścieżkami;
katalogi muszą już istnieć. Nie przekazuje się wartości kluczy w argumentach.

```bash
python -m scripts.mail_queue_key_backup init-key --destination /prywatne/klucz-kopii/key.json
python -m scripts.mail_queue_key_backup backup --source /prywatne/poczta/keys.json --backup-key /prywatne/klucz-kopii/key.json --destination /prywatne/archiwa/keys.mailkeybackup
python -m scripts.mail_queue_key_backup restore --archive /prywatne/archiwa/keys.mailkeybackup --backup-key /prywatne/klucz-kopii/key.json --destination /prywatne/odzyskane/keys.json
```

`init-key` generuje niezależny losowy klucz 256-bitowy w istniejącym formacie
wersjonowanych kluczy. Wyniki zawierają wyłącznie stałe pola powodzenia.
Błędy, także błędne argumenty CLI, zwracają stały kod
MAIL_KEY_BACKUP_REJECTED, bez prywatnej ścieżki, wyjątku i zawartości.

## Format i odtwarzanie

Archiwum ma nagłówek WPMKEY1, identyfikator wersji klucza szyfrującego i
losowy nonce 96-bitowy. AES-256-GCM uwierzytelnia zawartość i cały nagłówek.
Szyfrowany jest kanoniczny dokument kluczy w pamięci. Limit wielkości archiwum
jest sprawdzany przed deszyfrowaniem. Dokument odszyfrowany przechodzi ten
sam walidator formatu, duplikatów, wersji i Base64 co prywatny loader.
Plik docelowy jest publikowany dopiero po uwierzytelnieniu i walidacji,
atomowo i bez nadpisywania. Nie zapisuje się jawnego pliku tymczasowego
przed uwierzytelnieniem kopii.

Przed publikacją narzędzie ponownie sprawdza materiał i aktywną wersję
kluczy źródłowych oraz kluczy kopii i odmawia przy wykrytej zmianie.
Nie zastępuje to blokady rotacji po stronie operatora. Stare archiwum można odtworzyć po rotacji klucza
kopii, jeżeli historyczna wersja pozostaje w pęku szyfrującym. Usunięcie tej
wersji uniemożliwia otwarcie starej kopii. Narzędzie nie wykonuje automatycznej
rotacji ani usuwania kluczy; wymaga to osobnej procedury operatora.

Testy używają wyłącznie sztucznych kluczy. Próba lokalna odtwarza klucze do
oczekującego zadania SQLite i potwierdza brak zmiany zadania oraz później
obróconych kluczy aktywnych. Scenariusz PostgreSQL jawnie uruchamia dopiero
po odtworzeniu testowy proces ze sztucznym transportem. Nie ma automatycznej
aktywacji aplikacji, połączenia z dostawcą ani rzeczywistego doręczenia.

Przed użyciem operacyjnym pozostają niezależne miejsce przechowywania,
kontrola dostępu i procedura operatora, test odtworzenia bazy z kwarantanną
historycznych zadań oraz odbiór systemowych uprawnień i nadzorcy usługi.
