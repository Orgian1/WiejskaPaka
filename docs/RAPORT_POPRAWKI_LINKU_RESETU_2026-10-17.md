# Reset hasła w już otwartej karcie — 17.10.2026

Poprawiono przechwytywanie fragmentu `#reset-token=...` po nawigacji w już
załadowanej stronie. Formularz nasłuchuje `hashchange`, przenosi kod do pola
hasła i usuwa fragment z bieżącego wpisu historii. Wcześniej przechwycenie
wykonywało się tylko podczas pierwszego uruchomienia skryptu. Nowy test Node
wykonuje rzeczywisty skrypt z takim zdarzeniem, bez przeładowania dokumentu.

Diagnostyka natywnej bramy publikuje wyłącznie nazwy istniejących w repozytorium
plików testowych i numery linii. Nie publikuje treści błędów, parametrów,
tokenów, bezwzględnych ścieżek ani logów procesów. Osobny test sprawdza te
ograniczenia. Surowe XML i stdout/stderr nadal nie są artefaktami CI.

## Zakończone kontrole

Badany commit: `688f7defe0e9d4f95a905d8bc284100fccb7d088`.
Przebieg: https://github.com/Orgian1/WiejskaPaka/actions/runs/39053020840

| Kontrola | Wynik | Zakres |
| --- | --- | --- |
| Lokalne testy zmienionych obszarów | 55 PASS, 0 FAIL, 0 SKIP | Skrypt formularza, bezpieczna diagnostyka CI, launcher, kolejność skryptów i rzeczywisty HTTP resetu |
| Chromium w CI | 9 PASS, 0 FAIL, 0 SKIP | Poprzednie 7 przypadków oraz reset przez HTTP przy 390 i 1280 px |
| Kontrola viewportów HTTP | PASS | Pięć rozmiarów okna |
| PostgreSQL w CI | 15 PASS, 0 FAIL, 0 SKIP | Dotychczasowy natywny zestaw integracyjny; reset na PostgreSQL pozostaje wyłączony |

Raporty pobrano z artefaktów GitHub i zweryfikowano SHA-256 archiwów.
`audits/reset_ci_2026-10-17/browser.json` i `postgres.json` zawierają
liczniki, statusy i odciski kodu. Samo skonfigurowanie workflow nie jest
dowodem uruchomienia testów. Wcześniejszy przebieg dla `f2a22c7` miał 7 PASS
i 2 FAIL w Chromium; nie traktujemy go jako zaliczonego.

Windows wykonał 3658 przypadków: **3631 PASS, 3 FAIL, 24 SKIP**.
Ten przebieg nie jest zaliczony. Oczyszczony raport: `audits/reset_ci_2026-10-17/windows.json`.
Kolejną poprawkę opisuje `RAPORT_NAPRAWY_KOPII_WINDOWS_2026-10-18.md`.

## Ograniczenia

Nie podłączono rzeczywistej wysyłki e-mail, płatności, hostingu, domeny ani baz
użytkownika. Skrzynka resetu nadal służy wyłącznie syntetycznemu demo. Nie
zmieniono `main`. Wyniki nie oznaczają ukończenia wersji produkcyjnej ani
potwierdzenia Windows ACL, pełnej ochrony przed nadużyciami lub audytu prawnego.
