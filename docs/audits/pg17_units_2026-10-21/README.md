# PostgreSQL 17 i jednostki — weryfikacja CI

Gałąź preview/pg17-units-20261021 rozszerza Native test gates o osobne
PostgreSQL 16 i 17, z klientami backupu pasującymi do wersji serwera.
Nie korzysta z VPS: CI tworzy wyłącznie losowe bazy i role w swoim kontenerze.
Nowe trzy scenariusze sprawdzają sztuki, kilogramy i butelkę 0,75 l:
HTTP zakup, niezmienne metadane produktu/zamówienia, restart procesu,
anulowanie i zwrot magazynu tylko raz.

Preflight lokalny: 69 passed, 0 failed, 43 skipped. Pominięcia obejmują
rzeczywiste scenariusze PostgreSQL, ponieważ lokalnie brak klastra testowego.
Nie jest to dowód wykonania testów na PostgreSQL 17. Wynik CI wymaga odczytu.

Wcześniejszy run 39585853702 / commit 59268b0: PostgreSQL 16, Chromium
i szybki Windows zakończone sukcesem; pełny Windows był jeszcze w toku
w chwili przygotowania tego zapisu.

## Potwierdzony run 39587072873 / commit 8f08e69

Raporty native_8f08e69/: Windows pełny 4092 passed, 0 failed, 155 skipped;
szybki Windows 80/80; PostgreSQL 16 47/47, w tym trzy nowe scenariusze
jednostek; Chromium 36/36 plus HTTP w pięciu viewportach. Raporty mają
complete=true, success=true i sources_unchanged=true.

PostgreSQL 17 nie uruchomił testów: instalacja postgresql-client-17
nie znalazła pakietu w podstawowym repozytorium Ubuntu 24.04.
Poprawka workflow dodaje oficjalny podpisany repozytorium PGDG tylko
w zadaniu wersji 17. Wynik ponowionego zadania wymaga osobnego odczytu.
Źródło konfiguracji: https://www.postgresql.org/download/linux/ubuntu/

Kontrola skryptu postgres_test_backup wykryła również bramkę dopuszczającą
wyłącznie klienta 16. Zmieniono ją na jawną listę wersji 16/17; dodano testy
obu programów (pg_dump i pg_restore), w tym odrzucanie 15/18/beta.
Lokalny preflight używa teraz requirements-lock.txt; rezultat w
client-versions-preflight.json. Native PostgreSQL 17 nadal wymaga wyniku CI.

Starszy run 39585853702 miał timeout modułu test_crash_checkout_http.py
na Windows (brak wyniku modułu), a nie potwierdzony błąd asercji.
Nowszy run 39587072873 zakończył pełny Windows bez timeoutów i błędów.
Nie przypisujemy poprawki logiki aplikacji temu pojedynczemu timeoutowi.
