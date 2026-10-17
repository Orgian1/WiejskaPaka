# WiejskaPaka — kontynuacja 16 października 2026

Sprawdzony commit kodu: `8d18242bde592336fb4a36a387681face9218b7c`.

Odcisk źródeł aplikacji: `9acd150ccde9421d02cc375dbf346d0613f7636016c8f008054d30f198fdcaf5`.

## Rezultat

Usunięto bezterminowe blokowanie zapasu przez nowe nieopłacone zamówienia.
Dodano atomowe wygaszanie rezerwacji po 30 minutach, limit 10 nieopłaconych
zakupów na konto oraz termin widoczny w interfejsie. Automatyczne zwolnienie
nie obejmuje opłaconych ani częściowo opłaconych przesyłek i nie wykonuje
żadnych operacji pieniężnych. To nadal środowisko testowe.

## Wykryte problemy i rozwiązania

1. Nowe nieopłacone zakupy mogły blokować magazyn bez końca. Termin jest teraz
   zapisany w bazie; zadanie uruchamia się przy starcie i co 30 sekund.
2. Nie było limitu równoczesnych nieopłaconych zakupów. Limit wynosi 10 na
   kupującego, przesyłka wielopozycyjna liczy się raz. Sprawdzenie jest wewnątrz
   transakcji i blokady operacji kupującego.
3. Nieudana płatność `failed_test` blokowała zwykłe anulowanie. Stan jest
   nieopłacony: możliwe są anulowanie bez zwrotu i wygaśnięcie rezerwacji.
4. Częściowo opłacona przesyłka z inną pozycją w stanie `failed_test` nie dawała
   się anulować procesem zwrotu. Teraz opłacone pozycje otrzymują pełny
   symulowany zwrot, a cały zapas wraca dokładnie raz.
5. Wygasłą nieopłaconą rezerwację można byłoby przenieść do realizacji przed
   przebiegiem automatu. Wysyłka i gotowość odbioru sprawdzają termin; opłacone
   przed terminem zamówienia można realizować później.
6. Brak migracji PostgreSQL mógłby pozostawić automat niesprawny. Start serwera
   wymaga tabeli rezerwacji; dostarczono migrację bez zmian w starszych
   zamówieniach. Compose korzysta z przypiętych zależności.

## Faktycznie uruchomiona weryfikacja

| Zakres | Wynik |
|---|---|
| Pełna regresja w osobnych procesach i bazach | 235 modułów; 2943 PASS, 0 FAIL, 13 SKIP |
| Nowe przypadki rezerwacji | 27 PASS; terminy, idempotencja, rollback, wyścigi, ochrona wpłat i całych przesyłek |
| Rzeczywiste HTTP wygaszania | 44 kontrole PASS, 17 liczonych wywołań API; cykliczny przebieg i restart |
| Stabilność rzeczywistego HTTP | 300.25 s; 2439 rund; 19129 żądań; 45263 kontroli |
| Lokalny pakiet akceptacyjny HTTP | 4 zadania PASS: loopback, zakup/dostawa/zwrot, wielu sprzedawców, prywatność/dostawa |
| Anonimowy dostęp | 79/79 prywatnych tras odrzuciło dostęp; 0 niejednoznacznych |
| Izolacja kont HTTP | 52 kontrole PASS |
| Nagłówki i cache HTTP | 13 kontroli PASS |
| Finanse | 20 001 kwot; 100 002 kontrole PASS z niezależnym wzorcem Decimal |
| Składnia | compileall backend/database/scripts i node --check obu plików web: PASS |
| PostgreSQL natywny | NIEZWERYFIKOWANY; 11 pominiętych przypadków |
| Chromium | NIEZWERYFIKOWANY; 2 pominięte przypadki |

SKIP nie oznacza PASS. Liczby żądań, rund i kontroli nie są liczbą odrębnych
testów pytest i nie są do niej dodawane. W teście HTTP rezerwacji terminy są
cofane wyłącznie w jednorazowej bazie syntetycznej; serwer wykonuje normalny
30-sekundowy przebieg. Żądania health podczas startu nie wchodzą do licznika
17 wywołań API. Nie czekano 30 minut w czasie rzeczywistym.

Pełna regresja i test stabilności potwierdzają niezmienność źródeł. Wcześniejsze,
przerwane raporty nie są dowodem wydania. Podczas rozwoju poprawiono także
izolację danych w nowym teście partiowania; końcowy przebieg nie ma błędów.

## Bezpieczeństwo i reguły biznesowe

Zwolnienie zapasu, status, zapis wygaśnięcia, zdarzenie i powiadomienia są
jedną transakcją. Awaria wycofuje wszystkie zmiany. Sprawdzono dwóch
pracowników i anulowanie klienta, a także wyścig płatność–wygaszenie.
Opłata dostawy pozostaje naliczana raz na przesyłkę, a nie na każdą pozycję.
Niedostarczenie z winy dostawcy zachowuje pełny zwrot wpłaty wraz z dostawą.
Kwoty pozostają całkowitymi groszami, bez float. PIN i prawa konsumenta
pozostają zachowane. Nie dodano numerów telefonów ani produkcyjnych integracji.

## Dostęp do kodu i granice

GitHub ponownie zwrócił 404 dla `Orgian1/WiejskaPaka`, a lista udostępnionych
kont jest pusta. Nie wykonano push ani nie zmieniano widoczności. Archiwum
zawiera pełne źródła i lokalną historię w `WiejskaPaka_git.bundle`.
Nie uruchamiano GitHub Actions ani usług płatnych.

Nie uzyskano działającego natywnego PostgreSQL ani Chromium. Nie powtarzano
identycznych nieskutecznych prób z poprzedniej sesji: initdb odmawiał pracy
jako root, a uruchomienie przeglądarki blokowały uprawnienia systemowe.
Dodano kolejny natywny test PostgreSQL, ale jego wynik jest SKIP.

Starsze zamówienia nie otrzymują wstecz terminów. Częściowo opłacone przesyłki
wymagają jawnego anulowania ze zwrotem; nie są automatycznie zwalniane.
Automat wymaga działającego serwera z lifespan i obsługuje partie maksymalnie
100 kandydatów. Limit na konto nie zastępuje ochrony przed masowym tworzeniem
kont. Testowe paragony idempotencji nadal przechowują testowy PIN i wymagają
oddzielnej ochrony oraz retencji przed wdrożeniem.

Nie deklarujemy gotowości produkcyjnej ani procentu ukończenia. Nadal brakuje
m.in. pełnego wyszukiwania geograficznego, docelowej weryfikacji sprzedawców,
kompletnych opłat punktów i rozliczeń rocznych oraz niezależnego przeglądu
RLS, retencji, reklamacji i odzyskiwania kont. Lista:
`docs/audits/OGRANICZENIA_I_DALSZE_PRACE.md`.

## Pliki dowodowe i uruchomienie

- `audit_continuation_final_regression.json`: JUnit wszystkich modułów.
- `audit_inventory_expiry_http.json`: rzeczywiste HTTP nowej funkcji.
- `audit_continuation_soak.json`: obciążenie i niezmienność źródeł.
- `audit_continuation_http_acceptance.json`: cztery bramy HTTP.
- `audit_continuation_anonymous_http.json`, `audit_continuation_security.json`.
- `audit_continuation_money.json`, `audit_continuation_summary.json`.
- `docs/REZERWACJE_MAGAZYNU.md`: działanie, migracja i ograniczenia.

Start lokalny i wymagania opisuje `README.md`. Używać wyłącznie danych testowych.
Weryfikację świeżo rozpakowanego archiwum dokumentuje osobny raport dołączony
obok archiwum; nie dopisuje on wyniku testu do pliku, który już przetestowano.
