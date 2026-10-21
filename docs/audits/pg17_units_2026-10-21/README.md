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
