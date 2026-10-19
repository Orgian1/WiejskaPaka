# Testowe HTTP dla zaszyfrowanej kolejki resetu

Nowe trasy POST `/auth/password-reset/request` i
`/auth/password-reset/confirm` są domyślnie wyłączone (404).
Istniejące `/auth/password-reset-test/*` zachowują dotychczasowe działanie.

## Jawne włączenie na jednorazowym środowisku

Wymagane są jednocześnie `WP_ENV=test` (lub `testing`),
`WP_ENABLE_QUEUED_PASSWORD_RESET=1`, `WP_ENABLE_MAIL_QUEUE=1` oraz
`WP_MAIL_QUEUE_KEYS_FILE` wskazujące prywatny zewnętrzny plik kluczy POSIX.
Format i uprawnienia opisuje `KLUCZE_KOLEJKI_POCZTY.md`.
Nie należy włączać jednocześnie `WP_ENABLE_TEST_PASSWORD_RESET=1`;
konflikt zatrzymuje uruchomienie stałym, pozbawionym sekretów kodem błędu.

SQLite inicjuje tabele testowe. PostgreSQL wymaga wcześniej zastosowanych
kontrolowanych migracji, osobnej lokalnej bazy testowej i dodatkowego
`WP_ENABLE_PG_TEST_PASSWORD_RESET=1`, zgodnie z ograniczeniami lokalnego
testowego resetu. Nie wolno stosować tej konfiguracji do bazy zdalnej.
Nowe trasy przeszły natywny odbiór HTTP w bramce PostgreSQL (40 PASS,
0 FAIL, 0 SKIP), obejmującej cztery nowe scenariusze. Raport i zgodność
odcisków źródeł: `audits/queued_reset_pg_http_88c4cad_2026-10-19/`.

## Zachowanie

Żądanie przyjmuje wyłącznie `email`, normalizuje i sprawdza adres.
Znany, nieznany i ograniczony limitem poprawny adres otrzymują tę samą
odpowiedź 202 z ogólnym komunikatem i `Cache-Control: no-store`.
Odpowiedź nie zawiera identyfikatora zadania, odbiorcy ani tokenu.
Istniejące trwałe limity wynoszą trzy próby na adres i 100 globalnie
w oknie 15 minut. Nieznany adres nie tworzy zadania.

Token i zaszyfrowane zadanie powstają w jednej transakcji. Awaria zapisu
zadania wycofuje także token i zmiany limitów. Błąd infrastruktury daje
ogólną odpowiedź 500, a nie fałszywe potwierdzenie trwałego zapisu.
Potwierdzenie przyjmuje `token` i `new_password`, zużywa wszystkie linki
konta i unieważnia jego sesje w jednej transakcji. Powtórzenie linku
jest odrzucane. Kolejka nie może później wysłać zużytego linku.

API nie tworzy kluczy, nie uruchamia pracownika i nie wywołuje SMTP.
Podgląd telefonu i izolowany runner usuwają z odziedziczonego środowiska
wszystkie trzy zmienne włączające i wskazujące klucze.

## Pozostały zakres

Pracownik z ograniczonymi uprawnieniami, potwierdzanie adresów,
retencja metadanych, kopia i rotacja kluczy, bezpieczne odtworzenie
oraz odbiór dostawcy i DNS pozostają osobnymi etapami. Interfejs strony
nie przełącza się automatycznie na te trasy. Funkcja nie jest odbiorem
produkcyjnym i nie uruchamia rzeczywistych wysyłek.
