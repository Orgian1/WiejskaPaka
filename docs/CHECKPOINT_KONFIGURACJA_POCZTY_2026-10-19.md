# Checkpoint — zamknięcie testów przed serwerem, 19.10.2026

Kod: a9d7cbbb6a2c806ef4099f24be37d48e97bff83a.
Gałąź: preview/mail-configuration-check-20261019.
Roboczy PR: https://github.com/Orgian1/WiejskaPaka/pull/17
CI: https://github.com/Orgian1/WiejskaPaka/actions/runs/39287988285
Status całego przebiegu: completed / success.

## Wyniki badanego kodu

| Bramka | Wynik |
| --- | --- |
| Pełny Linux, 326/326 modułów | 4066 PASS, 0 FAIL, 68 SKIP |
| Pełny Windows | 3982 PASS, 0 FAIL, 152 SKIP |
| Natywny PostgreSQL 16 | 44 PASS, 0 FAIL, 0 SKIP |
| Chromium | 36 PASS, 0 FAIL, 0 SKIP; HTTP w pięciu rozmiarach: sukces |
| Szybki Windows | 80 PASS, 0 FAIL, 0 SKIP |
| Lokalny pakiet kontrolny | 108 PASS, 0 FAIL, 1 SKIP |

Pakiety nakładają się — nie sumować wyników i nie liczyć SKIP jako PASS.
Dowody i provenance: audits/mail_config_a9d7cbb_2026-10-19/.
Zweryfikowano SHA-256 archiwów, zgodność odcisków kodu, testów, zależności
oraz workflow. Wszystkie bramki complete/success/sources_unchanged.
Linux: cztery izolowane części, jeden odcisk aplikacji, komplet unikalnych
modułów i odciski każdego testu; raport nie publikuje przechwyconych logów.

## Wykonany zakres

Lokalna kontrola konfiguracji SMTP i kluczy kolejki używa istniejących
walidatorów. Stałe statusy, brak sieci, wysyłki, zapisów i startu pracownika.
Nie aktywuje konfiguracji. Kod wyjścia 0 oznacza tylko gotowość lokalnych
ustawień do kolejnej próby połączenia, nie dowód działania dostawcy.
Plan: PODLACZENIE_SERWERA_I_POCZTY_2026-10-20.md.

Bazowa poprawka diagnostyczna 0030dcf ma także zamknięty odbiór:
pełny Windows 3978 PASS / 0 FAIL / 146 SKIP, PostgreSQL 44, Chromium 36,
szybki Windows 80. Dowody: audits/ci_diagnostics_0030dcf_2026-10-19/.

## Starszy błąd — zachowany, nie uznany za naprawiony

Pierwsza próba kodu 20df26b: pojedynczy błąd test_checkout_vault_http.py;
raport pozostaje w audits/mail_key_backup_20df26b_2026-10-19/.
Próba 2 przebiegu 39278599502: startup_failure, pusta lista zadań.
Nie jest to ponowne wykonanie testu. Nowsze pełne regresje przeszły, ale
nie ustalają przyczyny tamtej awarii. Nie ponawiać starych testów bez końca;
przy powtórzeniu wykorzystać diagnostykę pliku/linii nowego runnera.

## Punkt wznowienia

Zaplanowana seria testów bez zakupionego VPS jest zamknięta. Bez nowej
zmiany kodu lub konkretnego problemu nie powtarzać zaliczonych regresji.
Domena już jest, serwer opłacony; dostęp do serwera i poczty oczekiwany 20.10.
Następny etap: rzeczywisty prywatny podgląd według instrukcji podłączenia,
kontrola restartu, uprawnień, kopii i próba dostarczenia poczty.
Zakres: POZOSTALE_PRACE_DO_PODGLADU_2026-10-19.md.

Zamknięcie testów nie oznacza zakończenia wszystkich prac przed publiczną
sprzedażą. Konto/rola/nadzorca pracownika, potwierdzanie adresów, odbiór
usług i kopii oraz zakres publicznego startu pozostają opisane w planie.
Nie scalono PR, nie uruchomiono SMTP, publicznego hostingu ani płatności.
