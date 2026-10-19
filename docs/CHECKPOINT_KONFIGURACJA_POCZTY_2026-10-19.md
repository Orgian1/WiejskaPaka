# Checkpoint przygotowania konfiguracji poczty — 19.10.2026

Gałąź: preview/mail-configuration-check-20261019.
Baza: 0030dcfda4d71abc1b47c0da65afc6e5f6212908, PR #16.
Domena już jest, serwer opłacony; aktywacja serwera i poczty oczekiwana 20.10.

Dodano scripts/check_mail_configuration.py: lokalny odczyt i walidacja
konfiguracji SMTP oraz kluczy kolejki istniejącymi walidatorami. Raport
zawiera stałe statusy, bez sekretów. Brak sieci, wysyłki, zapisów i startu
pracownika. Nie aktywuje konfiguracji. Kod 0 tylko gdy oba komponenty VALID;
nie jest dowodem połączenia z dostawcą ani dostarczenia wiadomości.

Plan: PODLACZENIE_SERWERA_I_POCZTY_2026-10-20.md.
Kontrola lokalna: 108 PASS / 0 FAIL / 1 SKIP (kontrola konfiguracji,
adapter SMTP, klucze kolejki i runner CI). Testy blokują próby sieciowe,
sprawdzają błędne pliki, prywatność raportu i brak zmiany plików.
To pakiet kontrolny; nie zastępuje pełnej regresji nowego kodu.

Odebrano trzy bramki CI 39285078185 dla bazowej poprawki 0030dcf:
PostgreSQL 44/44, Chromium 36/36 plus HTTP w pięciu rozmiarach,
szybki Windows 80/80. SHA-256 archiwów i wszystkie odciski zgodne
z izolowanym archiwum badanego commita. Raporty:
audits/ci_diagnostics_0030dcf_2026-10-19/.
Pełny Windows tej poprawki oraz ponowiony Windows starszej kopii kluczy
39278599502 nadal wymagają odbioru. Oddzielna gałąź zachowuje bieżący CI.
Pełny Windows kwarantanny 30de9b8 potwierdzony wcześniej: 3972/0/146.

Punkt wznowienia: odebrać powyższe Windows oraz nowy CI narzędzia
konfiguracji. Po aktywacji usług wykonać plan podłączenia na sztucznych
danych; konfiguracja konta i nadzorcy pracownika nadal pozostaje do wykonania.
Nie scalono PR, nie podłączono SMTP, publicznego hostingu ani płatności.
