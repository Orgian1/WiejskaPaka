# Odbiór demo WiejskaPaka — 20 listopada 2026

Gałąź `release/wiejskapaka-demo-zatwierdzony-20261120` powstała z zapisu `52036fd` z 19 listopada, z godziny 22:25 czasu polskiego. To najnowszy zapis znaleziony w gałęziach repozytorium. Pierwszy commit tej weryfikacji to `e592169`. W tym commicie katalog `web/` był identyczny z wersją `52036fd`. Skrypt kontrolny potwierdził zgodność `index.html`, `style.css` i `app.js` ze wzorcem zatwierdzonym przez właściciela.

## Uruchomienie na Windows

1. Pobierz ZIP z gałęzi. W Eksploratorze Windows kliknij archiwum prawym przyciskiem, wybierz **Wyodrębnij wszystkie** i otwórz rozpakowany katalog zawierający foldery `scripts` i `backend`.
2. Otwórz `START_DEMO_WINDOWS.cmd`. Przy pierwszym starcie skrypt przygotuje środowisko Pythona i pobierze przypięte wersje pakietów. Wymagany jest Python 3.12.
3. Otwórz [http://127.0.0.1:8766](http://127.0.0.1:8766). Konta demonstracyjne są wypisane w oknie uruchomienia. Dane przykładowe powstają w tymczasowej bazie dla tego uruchomienia.
4. Sprawdź układ katalogu, menu, koszyka i panelu sprzedawcy na komputerze oraz w widoku mobilnym. Otwórz portfel każdym kontem. Oczekiwany wynik to dwie różne reklamy, czerwony X z odliczaniem pięciu sekund, automatyczne zamknięcie i brak powtórki po ponownym wejściu przed upływem 30 minut.
5. Na szerokim ekranie sprawdź miejsca reklamowe w wolnych kolumnach paneli klienta i sprzedawcy. W portfelu reklama jest po lewej od „Praw konsumenta”. Treść bierze się z kampanii „Klient” lub „Sprzedawca” w sekcji „Reklamy w panelach i przy logowaniu”.
6. Wyloguj się i wybierz „Zaloguj się”. Nad formularzem pojawi się kampania „Logowanie – klienci”, a jeśli nie jest aktywna, kampania „Klient”.
7. Złóż zamówienie testowe i potwierdź odbiór PIN-em. Po odbiorze sprawdź jedną ocenę od 1 do 5 gwiazdek. W panelu sprzedawcy sprawdź punkt promocyjny i termin jego ważności.

## Wyniki weryfikacji

| Zakres | Wynik |
|---|---|
| Pełna regresja modułów | 442 moduły, 5208 zaliczonych, 0 błędów, 111 pominięć w przebiegu podstawowym |
| Chromium | 136 zaliczonych przypadków z modułów przeglądarkowych w pełnej regresji oraz 5 rozmiarów okna w oddzielnym teście |
| PostgreSQL 16.2 z FORCE RLS | 108 zaliczonych testów API i izolacji bazy |
| PostgreSQL 16.2 w trybie zgodności | 109 zaliczonych testów |
| GitHub Actions | 5 zadań zakończonych sukcesem, w tym start demo na Windows |
| Migracje | 52 sprawdzone skrypty, zgodne sumy, poprawne wdrożenie i cofnięcie bramki RLS z zachowaniem danych próbnych |

W przebiegu podstawowym 109 przypadków wymagało uruchomienia bazy PostgreSQL i zostało wykonanych w zestawach PostgreSQL. Dwa przypadki dotyczą odmowy dostępu do kluczy na systemie innym niż POSIX i zostały pominięte na Linuksie. [GitHub Actions dla kodu aplikacji](https://github.com/Orgian1/WiejskaPaka/actions/runs/44701804505).

Test startu z rozpakowanego archiwum uruchomił `run_phone_demo.py --full-demo` i otrzymał odpowiedź HTTP 200 z plikami zatwierdzonego widoku. Osobny przebieg potwierdził odbiór, dostawę, jednorazowy PIN, prywatność adresu i kwoty w groszach.

## Rozliczenia i baza

- Promocja obejmuje trzy punkty bez obciążenia portfela. Okres aktywowanego punktu to 30 dni, liczonych jako 720 godzin od aktywacji. Cena odnowienia wynosi 1000 groszy. Odnowienie odpłatne jest w tym demo wyceną. Portfel i rozliczenia używają danych testowych.
- Wypłaty testowe zachowują prowizję 5% dla sprzedawcy i 0% dla klienta. Opłaty za przesyłkę są naliczane w groszach, jednokrotnie dla wspólnej przesyłki.
- Punkty z wygasłym okresem są niedostępne w katalogu punktów i w obu ścieżkach zakupu. Bezpośredni endpoint zachowuje zgodność ze starszymi punktami bez zapisanego okresu. Publiczna lista wyboru i koszyk wymagają aktywnego okresu.
- Zatwierdzony spis jednorazowych migracji zawiera 52 pliki SQL z sumami kontrolnymi. Bramkę FORCE RLS można odtworzyć poleceniem `python -m scripts.run_rls_api_gate` po instalacji `requirements-security-test.txt`. Przygotowuje odizolowany PostgreSQL na loopbacku oraz uruchamia testy istniejących tras przez ograniczoną rolę aplikacji.
- Odbiór widoku na komputerze właściciela pozostaje osobnym krokiem. Demo lokalne startuje na SQLite z fikcyjnymi danymi. Próby RLS odbyły się na osobnej bazie PostgreSQL. Produkcyjna integracja PayU pozostaje poza tym odbiorem.
