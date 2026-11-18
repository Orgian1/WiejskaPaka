# WiejskaPaka — końcowa kontrola zatwierdzonego demo (2026-11-18)

## Wersja i bezpieczeństwo
- Gałąź robocza: `feat/zatwierdzony-widok-gwiazdki-reklamy-rls-20261118`.
- Kopia niezmiennego widoku: `backup/WIDOK-ZATWIERDZONY-PRZEZ-WLASCICIELA-20261118`.
- Nie scalać z gałęziami zawierającymi odrzucony wygląd.
- Trzy pliki `web/index.html`, `web/style.css`, `web/app.js` są chronione kontrolą `scripts/check_approved_ui.py`.
- Testy GitHub Actions nr 107 zakończyły się sukcesem, w tym Chromium dla obu ról. To nie zastępuje sprawdzenia na komputerze właściciela.

## Ostatni test lokalny (Windows PowerShell)
1. Otwórz PowerShell w katalogu **tej gałęzi** projektu; nie używaj starego katalogu z odrzuconym widokiem.
2. Uruchom `python scripts/check_approved_ui.py` w aktywnym środowisku Pythona.
3. Uruchom `python scripts/run_phone_demo.py --full-demo --port 8766`.
4. Otwórz `http://127.0.0.1:8766` i użyj wyłącznie danych demonstracyjnych wyświetlonych w terminalu.
5. Potwierdź wygląd listy produktów, menu, koszyka, ulubionych i panelu sprzedawcy.
6. Konto klienta: wejście do portfela pokazuje reklamę z czerwonym X i licznikiem 5 sekund; reklama zamyka się automatycznie; ponowne wejście przed upływem 30 minut nie pokazuje jej ponownie.
7. Konto sprzedawcy: powtórz test portfela i sprawdź odrębną kampanię.
8. Konto klienta: sprawdź gwiazdki przy produktach; ocenę 1–5 można wystawić tylko do własnego zakończonego zamówienia i tylko raz.
9. Sprawdź, że funkcje portfela i płatności działają **wyłącznie w trybie testowym**, a dane demo są fikcyjne.

## PostgreSQL — oddzielna bramka przed produkcją
- Migracja `migrations/20261118_seller_ratings_postgres.sql` jest przygotowana, **nie została uruchomiona na produkcji**.
- Przed migracją: kopia zapasowa, przegląd schematu i roli aplikacji, uzgodnienie uprawnień SELECT/INSERT oraz polityk RLS na tabeli `orders`.
- Po wdrożeniu na **oddzielnym środowisku testowym PostgreSQL** uruchom `python -m scripts.check_seller_ratings_postgres` z `DATABASE_URL` wskazującym rolę aplikacji. Skrypt jest tylko do odczytu i powinien zakończyć się kodem 0.
- Nie publikuj adresu `DATABASE_URL`, haseł, tokenów ani danych osobowych w GitHub Actions lub zgłoszeniach.
- Przed produkcją sprawdź również realne próby autoryzacji dla różnych klientów, ponowną ocenę, brak UPDATE/DELETE, działanie sesji i RLS, a także zgodność płatności z operatorem.
- Bez powyższych potwierdzeń PR pozostaje **draft**, bez scalenia i wdrożenia.
