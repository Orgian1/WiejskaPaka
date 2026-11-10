# WiejskaPaka — brama wdrożenia poprawki nagłówka (2026-11-09)

## Zweryfikowano
- PR #50: publiczne linki „Zaloguj się” i „Zarejestruj się”, przełączane po zalogowaniu na „Moje konto”.
- GitHub Actions run 42678198717: **success**, wszystkie 5 zadań: windows_recovery, windows, chromium, postgres 16, postgres 17.
- PR #50 jest oparty na gałęzi `preview/wallet-integrity-check-20261026` (PR #49), a nie bezpośrednio na `main`.
- Łańcuch PR: #50 → #49 → #48 i wcześniejsze gałęzie. **Nie scalać PR #50 wprost do `main` bez uzgodnienia całego łańcucha.**

## Czynności wymagające dostępu do wdrożenia
1. Ustalić commit rzeczywiście uruchomiony na VPS i sprawdzić stan repozytorium (w tym zmiany niezacommitowane). Nie nadpisywać lokalnych zmian.
2. Wykonać kopię zapasową aplikacji i bazy danych zgodną z istniejącą procedurą oraz zweryfikować możliwość przywrócenia.
3. Porównać VPS z bazową gałęzią PR #50 i rozstrzygnąć rozbieżności.
4. Dopiero po uzgodnieniu historii wdrożyć zatwierdzony commit na środowisko testowe.
5. Przetestować na telefonie i komputerze: gość → logowanie → panel klienta/sprzedawcy → wylogowanie → rejestracja; ponownie sprawdzić koszyk, zamówienia, PIN, portfel i rozliczenia.
6. Produkcyjne płatności i wypłaty pozostawić wyłączone do czasu uzgodnienia z operatorem i kontroli prawnej.

## Granice potwierdzenia
Przejście CI potwierdza skonfigurowane testy gałęzi, **nie** stan serwera VPS ani gotowość płatności produkcyjnych. PR #50 nie jest wdrożeniem.
