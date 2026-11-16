# Niezależny przegląd — reklamy portfela, 2026-11-16

Źródła: web/wallet-ads.js, backend/wallet_ads.py z gałęzi integration/demo-final-candidate-20261116. Przegląd statyczny, bez uruchomienia aplikacji.

## Potwierdzone w kodzie
- Frontend przechwytuje kliknięcie #wallet-nav-link i pokazuje modal.
- Licznik od 5, X disabled, zamknięcie automatyczne po 5000 ms czasu aktywnego JS.
- 2 s timeout zapytania o reklamę; błędy otwierają portfel bez reklamy.
- Serwer blokuje rekord konta FOR UPDATE w PostgreSQL i sprawdza 1800 sekund od poprzedniej emisji.
- Klucz request_key jest unikalny per konto; kliknięcie zapisywane jako boolean.
- Panel administracyjny, daty, obrazy i URL są walidowane; obrazy są rekodowane do JPEG.
- Zmiana sesji/wylogowanie unieważnia odpowiedzi.

## Rzeczy wymagające odbioru lub decyzji
1. Emisja oznacza przydzielenie banera przez serwer, a nie potwierdzenie 5 sekund obejrzenia. Rozłączenie może zużyć 30-minutowy limit bez wyświetlenia.
2. Licznik zależy od wykonywania JS w przeglądarce. Zawieszona karta może zamknąć reklamę później.
3. Obecny kod zapisuje last_shown=now+1; nominalny limit jest przez to o około sekundę dłuższy od 1800 sekund. Warto poprawić przed produkcją, jeżeli wymagana jest dokładna granica.
4. Żądanie z adblockera lub zmodyfikowanego klienta może pominąć modal. Nie traktować reklamy jako mechanizmu bezpieczeństwa.
5. Nie zweryfikowano tutaj rzeczywistych ACL, kluczy, restore backupu ani działania na VPS.
6. Brak workflow runs/status checks dla dokumentacyjnego commita kandydata w sprawdzonym API GitHub; raporty testowe są dostarczone przez Codex, nie są niezależnym uruchomieniem w tej kontroli.

## Brama wdrożeniowa
Przed wdrożeniem: odtworzyć testy na izolowanym PostgreSQL, wykonać testy przeglądarki i sprawdzić migracje 001/002/003 na kopii; zachować produkcyjną bazę i działający preview bez zmian. Nie podłączać PayU.
