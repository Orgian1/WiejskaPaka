# Kopia PostgreSQL i przygotowanie serwera — 18.10.2026

Badany kod: `cd9ca52206111621efa462d98df55311833dad90`.
CI: https://github.com/Orgian1/WiejskaPaka/actions/runs/39145936515
Zmiany: https://github.com/Orgian1/WiejskaPaka/pull/4

## Gotowe i sprawdzone

Dodano szyfrowaną kopię lokalnego PostgreSQL 16 z kluczem sejfu odpowiedzi
zakupowych. Klucz kopii jest niezależny i przechowywany poza katalogiem
archiwów. Publikacja nie zastępuje istniejącego pliku; proces dumpu ma
limit czasu i rozmiaru oraz nie zapisuje jawnego dumpu na dysku.

Próba odtworzenia najpierw uwierzytelnia archiwum, następnie tworzy nową
losową bazę. Sprawdza odczyt zaszyfrowanych odpowiedzi oraz spójność
symulowanych płatności; usuwa odzyskane sesje i tokeny resetu. Bazę próby
usuwa również po błędzie. Nie uruchamia aplikacji z odzyskanej kopii.

Natywny scenariusz zakłada konto sprzedawcy/rolnika i klienta, tworzy zakup,
rejestruje płatność testową, wykonuje prawdziwe pg_dump/pg_restore 16,
sprawdza liczniki i odszyfrowanie oraz potwierdza, że źródłowa sesja nadal
działa, a ponowienie źródłowego zakupu zwraca tę samą odpowiedź.

| Bramka | Zaliczone | Błędy | Pominięte |
| --- | ---: | ---: | ---: |
| Pełny Linux, 316/316 modułów | 3853 | 0 | 44 |
| Pełny Windows, kompletny | 3833 | 0 | 64 |
| PostgreSQL 16, w tym kopia/odtworzenie i restart | 22 | 0 | 0 |
| Chromium i osobny odbiór HTTP w 5 rozmiarach | 36 | 0 | 0 |
| Szybki Windows | 80 | 0 | 0 |

Wszystkie bramki zakończyły się sukcesem. Pełny Windows ma 3897 przypadków,
bez błędnych, niekompletnych lub przekroczonych czasowo modułów.
Nie zastępuje go szybki zestaw 80 przypadków. Lokalne zestawy
celowane (101 i 73) pokrywają się ze sobą i z pełną regresją — nie sumować.
Pominięcia są zależne od platformy i dostępności natywnych usług/przeglądarki.
Windows pomija także 5 przypadków runnera pipe POSIX; PostgreSQL oraz
Chromium mają odrębne wykonania bez SKIP. Nie uznawać pominięć za PASS.

## Przygotowanie na zakup serwera

- `URUCHOMIENIE_PODGLADU_NA_SERWERZE.md` i `deploy/preview/`: jednostka
  systemd, prywatna konfiguracja i jawna kolejność założenia nowej bazy.
- `KOPIA_POSTGRESQL_I_PROBA_ODTWORZENIA.md`: polecenia kopii, próby oraz
  ograniczenia; to narzędzie do małego środowiska testowego, limit 64 MiB.
- `POCZTA_STAN_KODU_I_ODBIOR.md`: sprawdzony stan poczty; brak SMTP,
  weryfikacji adresu i resetu hasła na PostgreSQL. Zakup skrzynki nie
  stanowi ich implementacji.

## Granice odbioru

Nie zakupiono serwera ani poczty, nie wdrożono jednostki systemd i nie
wykonano jej restartu na docelowym VPS. Nie uruchomiono zewnętrznych
połączeń, automatycznych kopii poza serwerem ani rzeczywistych płatności.
Próba dotyczy małego syntetycznego zbioru; nie potwierdza skali 5000 lub
500000 klientów dziennie, PITR ani gotowości produkcyjnej.

Źródła aplikacji backend/web/database i zasady sprzedaży pozostają takie
jak przed pakietem; zmiany dotyczą narzędzia, testów i przygotowania.
Rolnik i sprzedawca nadal oznaczają tę samą rolę.

## Dowody

Oczyszczone raporty znajdują się w
`docs/audits/postgres_backup_cd9ca52_2026-10-18/`. Dla pobranych artefaktów
sprawdzono SHA-256 archiwum względem metadanych GitHub oraz zgodność
skrótów źródeł, testów, zależności i workflow z badanym checkoutem.
Raporty nie zawierają dumpów, haseł, kluczy, DSN ani linków resetu.
