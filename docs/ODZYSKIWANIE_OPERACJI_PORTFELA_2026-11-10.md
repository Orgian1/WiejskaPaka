# Odzyskiwanie nierozstrzygniętych operacji portfela

Kontynuacja PR #52. Wyłącznie prywatny portfel demonstracyjny,
WP_ENABLE_WALLET_PREVIEW=1 w środowisku test/development. Bez PayU, banku,
rzeczywistych środków ani zmian na VPS.

## Obsługa

Po utracie odpowiedzi lub błędnym PIN-ie lokalny zapis operacji może blokować
zmianę kwoty. W formularzu doładowania/wypłaty i przy zapisanej nierozstrzygniętej
operacji dostępny jest przycisk „Sprawdź poprzednią operację”.

Serwer rozstrzyga jedno z dwóch zdarzeń:

- Operacja już zapisana: zwraca jej rzeczywistą kwotę, rodzaj i aktualny stan.
  Nie wykonuje ponownego doładowania ani rezerwacji. Wypłata pozostaje w swoim
  stanie; nie jest automatycznie anulowana. Można ją anulować osobnym przyciskiem.
- Operacja niezapisana: trwale blokuje jej dotychczasowy identyfikator i pozwala
  rozpocząć nową operację z nową kwotą. Spóźniony poprzedni wniosek zostanie
  odrzucony, również po restarcie lub zmianie przesłanej kwoty/rodzaju.

Dopiero po potwierdzeniu przez serwer przeglądarka usuwa odpowiadający lokalny
zapis. Stara odpowiedź nie może usunąć nowszego identyfikatora ani odblokować
innej aktywnej operacji. Zmiana konta unieważnia wcześniejszy callback.
Podczas sprawdzania nie rozpoczyna się innej operacji finansowej; można odzyskać
właśnie zawieszoną operację, ale nie przerwać w ten sposób innego aktywnego żądania.

Uszkodzony JSON, nieprawidłowy identyfikator lub kwota w pamięci karty blokują
nową operację zamiast cichego nadpisania. Nie przechowuje się PIN-u, hasła,
tokenu ani salda w lokalnym zapisie operacji. Zapis jest rozdzielony per konto
oraz rodzaj operacji. Odczytany obiekt zawiera tylko kwotę i identyfikator;
nie kopiuje dodatkowych pól do API.

## Integralność i migracja

Endpoint POST /wallet/operations/reconcile-test jest uwierzytelniony i sprawdza
sesję w tej samej transakcji co rozstrzygnięcie. Dopuszcza klienta i sprzedawcę,
wyłącznie we własnym portfelu. Korzysta ze wspólnej blokady konta z doładowaniem
i wypłatą. Jednoczesne sprawdzenie i pierwotny zapis nie mogą jednocześnie
potwierdzić zwolnienia identyfikatora i zaksięgować tej operacji.

Nowa tabela wallet_preview_operation_fences przechowuje niezmienne negatywne
potwierdzenia. Nie zmienia salda, rezerwy, PIN-u ani rewizji finansowej. Zapis
jest rozdzielony per właściciel i klucz. Audyt wykrywa wpis finansowy z kluczem,
który został wcześniej zablokowany. Spóźniona zablokowana wypłata nie zużywa
kolejnych prób PIN-u. Samego PIN-u nie wymaga odczyt już zapisanej własnej
operacji ani zablokowanie niezrealizowanego identyfikatora.

Migracja optional_wallet_operation_fences.sql jest wymagana po obu wcześniejszych
migracjach portfela. Zaktualizowano manifest i checksumy. PostgreSQL: SELECT,INSERT,
bez UPDATE/DELETE na nowej tabeli; brak tabeli blokuje preflight i start modułu.
SQLite tworzy tabelę podczas instalacji modułu i chroni ją triggerami przed
UPDATE/DELETE. Nie wykonano migracji na VPS ani na danych użytkownika.

Przed wdrożeniem: kopia bazy i kluczy, próba odtworzenia, zatrzymanie zapisów,
przegląd migracji, wdrożenie na kopii i preflight. Nie usuwać negatywnych
potwierdzeń: późne ponowienie musi pozostać zablokowane. Powrót do kodu sprzed
tego pakietu wymaga wyłączenia portfela WP_ENABLE_WALLET_PREVIEW=0, ponieważ
stary kod nie respektuje nowych blokad. Zachować dane i pełny dziennik.

## Kontrola

1. W pełnym lokalnym demo zasymuluj utratę odpowiedzi doładowania lub błędny
   PIN wypłaty. Zmień kwotę: aplikacja ma zażądać sprawdzenia poprzedniej operacji.
2. Użyj przycisku sprawdzenia. Po zwolnieniu zapisu można podać nową kwotę.
   Jeśli operacja była zapisana, historia i saldo pokazują ją jednokrotnie.
3. Odświeżenie/restart i spóźniona odpowiedź nie mogą podwoić doładowania,
   rezerwacji ani skasować nowego zapisu operacji. Sprawdź telefon i komputer.

**Wszystkie 5/5 bramek CI zakończone sukcesem.**

Kod: `058f8b4d2ed2d99f805bf38649c42269fdeb06da`, PR #53.
CI: https://github.com/Orgian1/WiejskaPaka/actions/runs/42773045567.

| Zestaw | Wynik |
| --- | --- |
| Celowane testy odzyskiwania i pamięci karty | 21 PASS, 0 FAIL, 0 SKIP |
| PostgreSQL 16 | 97 PASS, 0 FAIL, 0 SKIP |
| PostgreSQL 17 | 97 PASS, 0 FAIL, 0 SKIP |
| Szybki Windows | 91 PASS, 0 FAIL, 0 SKIP |
| Chromium | 76 PASS, 0 FAIL, 0 SKIP + HTTP na 5 rozmiarach |
| Pełny Windows | 4639 PASS, 0 FAIL, 275 SKIP; 4914 przypadków, brak timeoutów i niekompletnych modułów |
| Lokalny Linux | 4753 PASS, 61 błędów startu Chromium, 100 SKIP; 4914 przypadków w 387 modułach |

Wszystkie lokalne błędy dotyczą systemowej blokady socketu Chromium, a nie
rozstrzygniętych asercji aplikacji. Lokalnego przebiegu nie oznaczono jako
sukcesu. Te scenariusze wykonano w CI bez błędów. Pominięte lokalnie scenariusze
natywnego PostgreSQL wykonano oddzielnie na wersjach 16 i 17. Zestawy częściowo
się pokrywają; nie sumować ich jako liczby różnych testów.

Testy przeglądarkowe obejmują spóźnione pierwsze żądanie, utratę odpowiedzi
po zapisie, spóźnioną odpowiedź sukcesu po rozpoczęciu nowej operacji oraz
błędny PIN i zmianę kwoty, na 320 i 1280 px. Pierwszy przebieg wykazał dwa błędy
samego predykatu oczekiwania w teście: CSP blokowała ewaluację tekstowego
wyrażenia. Diagnostyka potwierdziła zapis doładowania i widoczny błąd sieci
w formularzu. Predykat zastąpiono funkcją, bez osłabienia CSP aplikacji.
Końcowa bramka Chromium wykonała wszystkie przypadki pomyślnie.

Raporty i odciski źródeł: `audits/wallet_recovery_2026-11-10/`.
Końcowy zapis raportów zmienia tylko dokumenty i JSON. Drzewo przetestowanego
kodu jest też zachowane na gałęzi `integration/demo-main-20261110`, commit
`718ad0b9f0fc897aff7f296202442cb4e7b1ce3e`. Main i gałęzie wcześniejszych PR-ów
nie były zapisywane w tym pakiecie. Późniejsze zmiany zwykłego czatu są integrowane osobno. VPS nie był modyfikowany.
