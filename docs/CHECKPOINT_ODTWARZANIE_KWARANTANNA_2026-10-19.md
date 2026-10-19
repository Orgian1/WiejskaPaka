# Checkpoint odtworzenia bazy i kluczy — 19.10.2026

Kod: 30de9b86b2f20deb58027db9df64a0ad20b313be.
Gałąź: preview/mail-restore-quarantine-20261019.
Roboczy PR: https://github.com/Orgian1/WiejskaPaka/pull/16
Baza: preview/mail-key-backup-20261019 (PR #15; wcześniej #12–14).
CI: https://github.com/Orgian1/WiejskaPaka/actions/runs/39280581000

## Wykonany zakres

Odtwarzanie nowej kopii SQLite i kontrolowana próba PostgreSQL unieważniają
sesje/linki resetu oraz poddają kolejkę kwarantannie w jednej transakcji.
Queued i leased bez rozpoczęcia stają się expired; rozpoczęte próby stają
się uncertain. Usuwane są ładunki i dzierżawy. Zachowano liczbę prób,
historię zakończonych zadań i publiczny format dotychczasowych raportów.
Źródło nie jest modyfikowane. Zwykły backup nie uruchamia kwarantanny.
Szczegóły: ODTWARZANIE_BAZY_I_KLUCZY_POCZTY.md.

## Potwierdzona weryfikacja nowego kodu

- Pełny Linux: 4050 PASS, 0 FAIL, 68 SKIP; 325/325 modułów.
- Wszystkie cztery izolowane części: success, complete, sources_unchanged,
  jeden odcisk aplikacji; zapisano odciski modułów i ich liczniki.
- Dowód: audits/restore_quarantine_30de9b8_2026-10-19/linux-full.json.
- Pakiet kontrolny: 221 PASS, 0 FAIL, 42 SKIP.
- Węższy pakiet odtwarzania i istniejących kopii: 63 PASS, 0 FAIL.
- Pakiety kontrolne nakładają się na pełną regresję; nie sumować ich.
- Natywny PostgreSQL 16: 44 PASS, 0 FAIL, 0 SKIP.
- Chromium: 36 PASS, 0 FAIL, 0 SKIP; HTTP w pięciu rozmiarach: sukces.
- Szybki Windows: 80 PASS, 0 FAIL, 0 SKIP.
- Raporty i provenance zapisano obok linux-full.json; SHA-256 archiwów
  oraz odciski kodu, testów, zależności i workflow są zgodne.
- Pełny Windows nowej kwarantanny nadal wymaga odbioru.

Próba lokalna odtwarza zaszyfrowaną bazę i osobne klucze, sprawdza
expired/expired/uncertain, brak zadań dla transportu, zachowanie zamówień,
brak sesji/tokenów, niezmieniony skrót źródła oraz usunięcie niepełnego celu
po wymuszonej awarii. Test natywny wykonuje pg_dump/pg_restore do nowej
losowej bazy i kontroluje kwarantannę przed jej usunięciem — odbiór CI
został potwierdzony raportem PostgreSQL 44/44.

Drzewo lokalnego i zdalnego kodu:
df0bb2aa49c6c061af584cbd50d8012d9bc4ae92.

## Zamknięty odbiór wcześniejszej kopii kluczy

Dla commita 20df26b odebrano i zweryfikowano PostgreSQL 43 PASS / 0 FAIL /
0 SKIP, Chromium 36 PASS / 0 FAIL / 0 SKIP z HTTP w pięciu rozmiarach oraz
szybki Windows 80 PASS / 0 FAIL / 0 SKIP. Raporty i provenance są w
`audits/mail_key_backup_20df26b_2026-10-19/`.
Sprawdzono SHA-256 archiwów i wszystkie odciski źródeł/testów/zależności
względem izolowanego worktree badanego commita. Tych wyników nie wolno
przedstawiać jako odbioru nowej kwarantanny. Checkpoint kopii kluczy
zaktualizowano; pełny Windows pozostaje do osobnego odbioru.

## Punkt wznowienia

1. Odebrać pełny Windows CI 39280581000 dla kwarantanny.
2. Retencja: pełny Windows potwierdzony, 3965 PASS / 0 FAIL / 121 SKIP.
   Kopia kluczy: pierwsza próba 3965 PASS / 1 FAIL / 143 SKIP, moduł
   test_checkout_vault_http.py; wynik zachowano jako windows-attempt1.json.
   Odciski są zgodne. Log CI nie podaje konkretnej asercji. Próba ponowienia
   zadania 118149503175 została odrzucona HTTP 403: przebieg nadal running.
   Nie uznawać błędu za naprawiony ani losowy bez dalszej diagnozy.
3. Następnie potwierdzanie adresów, procedura operatora dla spójnych kopii
   i rotacji, konto/rola/nadzorca pracownika oraz osobny odbiór usług i DNS.

Nowa próba nie aktywuje aplikacji, kluczy ani wysyłek. Spójny produkcyjny
pakiet kopii i jego odbiór operacyjny pozostają osobnym zadaniem.
Nie scalono PR #12–16. Hosting i rzeczywiste płatności pozostają odłączone.

Kontrola lokalna aktualnego modułu test_checkout_vault_http.py: 5 PASS
w 40,39 s. Wynik Linux nie rozstrzyga przyczyny pojedynczego błędu Windows.
