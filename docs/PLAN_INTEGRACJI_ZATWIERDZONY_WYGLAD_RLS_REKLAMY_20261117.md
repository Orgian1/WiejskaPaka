# Integracja zabezpieczeń i reklam z zaakceptowanym wyglądem — 2026-11-17

## Nienaruszalna baza
Gałąź: `fix/approved-ui-description-200-20261117`, wyprowadzona z `codex/issue-60-separate-views-20261113`. Użytkownik osobiście potwierdził układ kart obok siebie, rozwijanie produktu, osobne widoki koszyka i portfela, licznik koszyka i serduszka. Nie wolno zastąpić `web/index.html`, `web/app.js`, `web/style.css` ani `web/app-views.js` plikami z gałęzi 2026-11-16.

## Źródło elementów do selektywnego przeniesienia
`WIEJSKAPAKA-FINAL-WYGLAD-RLS-REKLAMY-20261116`:
- `backend/rls_gateway.py`, `backend/rls_session_context.py`, `database/security_rls/`, `scripts/run_rls_api_gate.py` i testy RLS. Wymagają zgodnego połączenia z `backend/app.py` oraz adapterem PostgreSQL; samo skopiowanie plików NIE uruchamia RLS.
- `backend/wallet_ads.py`, `database/optional_wallet_ads.sql`, migracje `002_wallet_ads` i `004_wallet_ads_audience`, `web/wallet-ads.js` i testy reklam. Wymagają integracji z trasami aplikacji.
- W gałęzi źródłowej reklamy otwierają portfel przez `scrollIntoView` i `#wallet-section`, podczas gdy zatwierdzony interfejs używa `app-views.js` i osobnych tras. Bez adaptacji reklamy mogą psuć widoki albo dać się ominąć przez wejście na `#wallet`.

## Warunki odbioru
1. Wszystkie wejścia do portfela (kliknięcie, bezpośredni hash, powrót do widoku) przechodzą przez jeden kontrolowany mechanizm reklamy. Nie blokować portfela po błędzie serwera reklam; żadna reklama nie może pojawić się częściej niż raz na 30 minut na konto.
2. Osobne kampanie klienta i sprzedawcy; czerwony X z odliczaniem 5 sekund, zamknięcie automatyczne. Bez zmiany wyglądu pozostałych widoków.
3. Testy PostgreSQL FORCE RLS na izolowanej bazie; żadnych migracji na produkcji bez kopii zapasowej i osobnego zatwierdzenia.
4. Testy przeglądarkowe: katalog, opis i zdjęcie, koszyk, portfel, serduszka, punkty odbioru, oba typy kont.
5. Żadnego automatycznego scalenia całych gałęzi; dopiero po zielonych testach i kontroli wizualnej.

## Stan
To plan integracji, NIE potwierdzenie, że RLS lub reklamy zostały przeniesione. Zmiany w opisach i kompresji zdjęć są oddzielne i wymagają ukończonych testów.
