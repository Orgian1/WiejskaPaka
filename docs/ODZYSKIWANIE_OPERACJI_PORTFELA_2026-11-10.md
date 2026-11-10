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

Wyniki końcowe będą zapisane po zakończeniu testów tego pakietu.
