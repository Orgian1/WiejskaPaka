# Lokalna kopia i odtworzenie wersji testowej — 17.10.2026

Dodano `scripts/sqlite_snapshot.py`: spójna kopia SQLite przez Online Backup
API, kontrola integralności i relacji, weryfikacja klucza i wszystkich
zaszyfrowanych odpowiedzi zakupowych, audyt symulacji płatności. Odtworzenie
usuwa sesje odziedziczone z kopii przed udostępnieniem nowej bazy. Istniejące
cele nie są nadpisywane, błędna operacja usuwa własny częściowy katalog.
Źródło jest otwierane tylko do odczytu; brak połączeń z zewnętrzną bazą.

Weryfikacja bieżącego kodu na Linux: **3612 PASS, 0 FAIL, 17 SKIP**, wszystkie
286 modułów w sześciu grupach; każdy moduł w osobnym procesie i bazie.
Źródła nie zmieniły się podczas przebiegu. Odcisk kodu i oczyszczone wyniki:
`audits/sqlite_snapshot_2026-10-17.json`. Sam zestaw kopii i odtwarzania:
**16 PASS**, w tym 11 nowych przypadków. Sprawdzono aktywny WAL z niezatwierdzoną
zmianą ceny, zachowanie zakupów i pojedynczej opłaty za przesyłkę,
unieważnienie sesji, niewłaściwy klucz, uszkodzoną bazę, brak źródła,
odmowę nadpisania, prywatność komunikatu CLI i nieprawidłowe limity czasu.
`git diff --check` bez błędów. Nie powtórzono natywnych testów Windows,
PostgreSQL i Chromium po tej zmianie; ich wcześniejsze wyniki mają zakres
opisany w poprzednim raporcie.

Zaktualizowano listę odbioru: usunięto nieaktualne informacje o braku testów
natywnych i uwzględniono późniejszą zgodę na użycie GitHub.

## Pozostały zakres

To narzędzie dla lokalnego demo. Cała kopia pozostaje jawna, klucz jest obok
bazy; POSIX 0700/0600 nie zastępuje szyfrowanego magazynu ani Windows ACL.
Nadal potrzebne są harmonogram i retencja kopii, osobny magazyn kluczy,
odtworzenie PostgreSQL oraz rozstrzygnięcie cofniętych haseł i uprawnień.
Nie wdrożono odzyskiwania zapomnianego hasła ani produkcyjnych płatności,
hostingu i domeny. Cały projekt nie jest jeszcze ukończony produkcyjnie.
Nie zmieniono `main` ani danych użytkownika.
