# Odłączone wykonywanie kolejki na PostgreSQL

Stan: 19.10.2026. backend/reset_mail_queue.py obsługuje teraz jawnie przekazane
połączenie PgConnection oraz SQLite. Zmiana nie podłącza tras HTTP, dostawcy
poczty, pętli pracownika ani konfiguracji środowiskowej. Nie otwiera połączenia
przy imporcie. Nie wykonuje migracji. W testach używany jest wyłącznie
jednorazowy lokalny PostgreSQL i transport zastąpiony funkcją w pamięci.

## Transakcje i współbieżność

Wywołujący tworzy PgConnection z psycopg z dict_row. transaction() wymaga
bezczynnego połączenia, otwiera własną transakcję i odrzuca zagnieżdżenie.
Operacje niskiego poziomu wymagają aktywnej transakcji. dispatch_once
zatwierdza przejęcie, następnie znacznik rozpoczęcia, a dopiero potem
wywołuje transport poza transakcją. Na końcu zamyka połączenie.

Przejęcie zadania korzysta z FOR UPDATE SKIP LOCKED. Odzyskiwanie dzierżaw
i wygasłych zadań również pomija zajęte wiersze. Nie wykonuje zbiorczego
UPDATE oczekującego na taki wiersz. Start i wynik blokują właściwy wiersz
FOR UPDATE, sprawdzając właściciela, ważność dzierżawy i znacznik próby.
Spóźniony pracownik nie może nadpisać wyniku nowszego właściciela.

Szyfrowanie, sprawdzanie linku, limity, retencja szyfrowanego ładunku i kody
transportu pozostają wspólne ze SQLite. Próba rozpoczęta bez pewnego wyniku
jest uncertain bez automatycznego ponowienia. To ochrona przed duplikatami
po awarii, nie gwarancja dokładnie jednokrotnego dostarczenia przez SMTP.

Schema pochodzi z upgrade_z_reset_mail_queue.sql, wpisanej w kontrolowany
manifest migracji. Nie dodano nowej migracji w tym etapie. Rola natywnych
testów może wykonywać DML, ale nie tworzyć tabel ani zarządzać bazą.

## Zakres natywnego odbioru

Osiem nowych scenariuszy używa osobnych jednorazowych baz i ograniczonej roli:
wykonanie i brak ponowienia, rollback po błędzie SQL, brak zadania dla
nieznanego konta i limit, czterech równoległych pracowników, utrata dzierżawy
przed i po rozpoczęciu, pomijanie zablokowanych także wygasłych wierszy,
unieważnienie po resecie hasła oraz ograniczony backoff i liczba prób.

W wywołaniu transportu sprawdzany jest również trwały znacznik przez inne
połączenie, które może zablokować wiersz NOWAIT. To dowód zakończenia
transakcji przed transportem; nie jest testem rzeczywistego serwera SMTP.

## Co pozostaje

Potrzebne są integracja bezpiecznego ogólnego endpointu HTTP,
potwierdzanie adresów, retencja metadanych,
zasady odtwarzania kopii bez ponownych wysyłek oraz ograniczony proces
pracownika z uprawnieniami dobranymi do wdrożenia. Klucza kolejki nie ma
w istniejącym pakiecie kopii samej bazy i klucza sejfu zamówień.
Testy dostawcy, DNS i rzeczywistego dostarczenia wymagają osobnego odbioru.

Podstawy SQLite opisuje KOLEJKA_RESETU_SQLITE.md. Dla aktualnego wykonania
PostgreSQL ten dokument zastępuje jego wcześniejsze ograniczenie do SQLite;
nie zmienia faktu, że moduł pozostaje odłączony od aplikacji.

Jawny loader prywatnych wersjonowanych kluczy opisuje
KLUCZE_KOLEJKI_POCZTY.md. Odczyt pliku nie stanowi pełnego zarządzania kluczami
i nie uruchamia pracownika.
