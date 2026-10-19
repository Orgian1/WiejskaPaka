# Checkpoint kopii kluczy poczty — 19.10.2026

Kod: 20df26b139fb402ce67912a38b2ef0be9c81944f.
Gałąź: preview/mail-key-backup-20261019.
Roboczy PR: https://github.com/Orgian1/WiejskaPaka/pull/15
Baza: preview/reset-queue-retention-20261019 (PR #14; wcześniej #12–13).
CI: https://github.com/Orgian1/WiejskaPaka/actions/runs/39278599502

## Wykonany zakres

Jawne szyfrowanie wersjonowanego pęku kluczy poczty przez AES-256-GCM,
z niezależnym kluczem szyfrującym poza katalogiem archiwum. Odtwarzanie
uwierzytelnia i waliduje dokument w pamięci, a następnie atomowo publikuje
nowy prywatny plik bez nadpisania istniejącego. Nie zmienia konfiguracji
aplikacji, nie odtwarza bazy i nie uruchamia pracownika ani SMTP.

Kontroluje POSIX, własność i prawa plików/katalogów, dowiązania, rozmiary,
format wersji, duplikaty i Base64. Błędy funkcji i argumentów CLI są stałe,
bez prywatnych ścieżek i zawartości. Kopia zachowuje historyczne klucze
poczty; klucz szyfrujący można obrócić z zachowaniem starszej wersji do
odczytu dawnych archiwów. Nie dodano automatycznej procedury rotacji.
Szczegóły: KOPIA_KLUCZY_KOLEJKI_POCZTY.md.

## Potwierdzona weryfikacja

- Pełna lokalna regresja Linux: 4042 PASS, 0 FAIL, 67 SKIP; 324/324 moduły.
- Cztery izolowane części mają ten sam odcisk aplikacji, niezmienione
  źródła oraz success/complete/sources_unchanged.
- Dowód: audits/mail_key_backup_20df26b_2026-10-19/linux-full.json.
- Pakiet kontrolny: 179 PASS, 0 FAIL, 41 SKIP.
- Wcześniejszy węższy pakiet: 101 PASS, 0 FAIL, 2 SKIP.
- Wyniki pakietów nakładają się na pełną regresję; nie sumować ich.
- Nowy scenariusz natywny PostgreSQL odzyskuje klucze, odczytuje oczekujące
  zadanie i jawnie uruchamia proces ze sztucznym transportem. Próg bramki
  został podniesiony do 43. To przygotowany test, a nie wynik odbioru.

Aktualizacja po 17:39 Europe/Warsaw: odebrano i zweryfikowano trzy bramki
CI 39278599502: PostgreSQL 43 PASS, 0 FAIL, 0 SKIP; Chromium 36 PASS,
0 FAIL, 0 SKIP i HTTP w pięciu rozmiarach; szybki Windows 80 PASS,
0 FAIL, 0 SKIP. Raporty i provenance są w tym samym katalogu audits.
Zweryfikowano SHA-256 archiwów oraz wszystkie odciski względem izolowanego
worktree badanego commita 20df26b, a nie nowszej kwarantanny kolejki.
Pełny Windows kopii kluczy oraz retencji nadal wymagają osobnego odbioru.
Narzędzie nie wymaga własnego serwera użytkownika.

Drzewo lokalnego i zdalnego kodu jest identyczne:
d5550e4f8d10528256f9beb356b61ff1080677f1.

## Dokładny punkt wznowienia

Najpierw odczytać CI 39278599502 (kopia kluczy) oraz pełny Windows
39276035351 (retencja). Pobrać zakończone raporty, sprawdzić SHA-256
archiwów i zgodność odcisków z badanym commitem, zapisać provenance.
Dla kopii kluczy oczekiwany minimalny PostgreSQL to 43; nie przepisywać
liczby jako wyniku bez raportu. Dla retencji bazowe odciski są zapisane
w audits/queue_retention_30a632f_2026-10-19/postgres.json.

Następnie pozostają: potwierdzanie adresów, próba wspólnego odtworzenia
bazy i kluczy z kwarantanną historycznych zadań, procedura operatora
rotacji/archiwizacji kluczy oraz systemowe konto, rola i nadzorca pracownika.
Kopia samych kluczy nie stanowi spójnej kopii bazy ani pełnego odbioru
operacyjnego. Prawdziwa poczta, hosting i rzeczywiste płatności pozostają
odłączone. Nie scalono PR #12–15.

## Odbiór pełnego Windows — aktualizacja

Pierwsza próba: 3965 PASS, 1 FAIL, 143 SKIP. Nieudany moduł:
`test_checkout_vault_http.py`. Raport windows-attempt1.json i provenance
zachowują zweryfikowany SHA-256 archiwum i zgodne odciski. Log zadania
nie zawiera konkretnej asercji. Nie uznano wyniku za sukces ani awarię losową.
Próba ponowienia zadania 118149503175: HTTP 403, przebieg nadal running.
Retencja została osobno potwierdzona: 3965 PASS, 0 FAIL, 121 SKIP.
Nowsza kwarantanna ma potwierdzone PostgreSQL 44, Chromium 36 i szybki
Windows 80; pełny Windows tej wersji nadal do odbioru.

Kontrola lokalna aktualnego modułu test_checkout_vault_http.py: 5 PASS
w 40,39 s. Wynik Linux nie rozstrzyga przyczyny pojedynczego błędu Windows.
