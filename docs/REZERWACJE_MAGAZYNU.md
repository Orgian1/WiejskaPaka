# Rezerwacje magazynu — środowisko testowe

Nowe zakupy `/orders` i `/cart/checkout-test` mają termin rezerwacji 30 minut.
Termin jest zapisany w UTC w tabeli `inventory_reservations`, zwracany jako
`reservation_expires_at` i widoczny na liście zamówień. Koszyk przed zakupem
nie rezerwuje magazynu. Jedno konto może mieć maksymalnie 10 nieopłaconych
zakupów; przesyłka wielopozycyjna liczy się raz.

## Przebieg

Podczas startu FastAPI proces sprawdza obecność tabeli rezerwacji, następnie
uruchamia zadanie kontrolujące terminy od razu i co 30 sekund. Uvicorn musi
mieć włączony lifespan (domyślne `auto`); nie używać `--lifespan off`.
Po ponownym uruchomieniu zaległe rezerwacje są ponownie sprawdzane.
Jeśli aplikacja nie działa, zapas zostanie zwolniony dopiero po jej starcie.

Zadanie zwalnia towar tylko dla zamówień nadal oczekujących, bez potwierdzenia
PIN i bez zapłaty. Brak płatności, `awaiting_payment` i `failed_test` są stanami
nieopłaconymi. Zmiana statusu, zwiększenie zapasu, oznaczenie zwolnienia,
zdarzenie `reservation_expired_test` i powiadomienia są jedną transakcją.
Nie pobiera się prowizji ani nie wykonuje zwrotu za wygasłą rezerwację.

Cała przesyłka jest blokowana i sprawdzana razem. Każda opłacona pozycja
chroni przesyłkę przed automatycznym wygaszeniem. Dla częściowo opłaconej
przesyłki konieczne jest świadome dokończenie lub anulowanie z pełnym zwrotem
opłaconych pozycji; automat nie dokonuje potrąceń ani częściowego zwalniania.
Po terminie nie można dopłacić kolejnej nieopłaconej pozycji ani rozpocząć jej
realizacji. Opłacone przed terminem zamówienie można realizować później.

SQLite używa `BEGIN IMMEDIATE`; ścieżka PostgreSQL blokuje przesyłkę i jej
zamówienia w tej samej kolejności co inne operacje przesyłki. Zapis płatności
blokuje zamówienie przed sprawdzeniem terminu. Przywrócenie zapasu zależy od
jednorazowego przejścia statusu. Testy obejmują dwóch pracowników, anulowanie
klienta i wyścig z płatnością. Natywna ścieżka PostgreSQL nadal wymaga
uruchomienia w środowisku dopuszczającym serwer PostgreSQL.

## Aktualizacja lokalnej bazy

SQLite tworzy tabelę przy imporcie aplikacji. Dla PostgreSQL przed startem
należy zastosować `database/upgrade_b10921_inventory_reservations.sql`
w wyłącznie testowej bazie; rola aplikacyjna nie wykonuje DDL.
Nowa migracja nie nadaje terminów istniejącym zamówieniom. Brak tabeli
powoduje błąd startu serwera, zamiast wyłączać ochronę bez ostrzeżenia.

Idempotentne ponowienie zakupu zwraca historyczny paragon i jego pierwotny
termin, także po wygaszeniu. Nie rezerwuje ponownie towaru. Aktualny status
należy odczytywać z `/orders/me`, a nie ze starego paragonu. Powtórzenie już
zapisanego zdarzenia płatności może zwrócić jego wynik po terminie, lecz nie
wywołuje kolejnej płatności. Nowe zdarzenie po terminie jest odrzucane.

## Ograniczenia

Automat przetwarza maksymalnie 100 kandydatów w przebiegu (pełna przesyłka
może zawierać więcej niż jednego kandydata). Większa zaległość wymaga kolejnych
przebiegów. Nieprawidłowy rekord lub błąd bazy wycofuje przebieg, zapisuje
ogólny komunikat bez danych osobowych i powoduje ponowienie po 30 sekundach.
Monitorowanie takich błędów i ochrona przed masowym tworzeniem kont pozostają
pracami przedprodukcyjnymi. Limit na konto nie zastępuje ochrony antybotowej.
Nie zmieniono historycznej możliwości realizacji demonstracyjnego zamówienia
bez płatności przed terminem; to nadal nie jest proces produkcyjny.

## Powtarzalna weryfikacja

```bash
python scripts/run_tests_per_file.py test_b10921_inventory_expiry.py --report rezerwacje_pytest.json
python scripts/check_inventory_expiry_http.py --report rezerwacje_http.json
```

Drugi skrypt uruchamia rzeczywisty serwer na loopback, tworzy jednorazową bazę
i dane syntetyczne, cofa w niej terminy jako kontrolowaną daną testową, czeka
na normalny 30-sekundowy przebieg i osobno sprawdza odzyskanie po restarcie.
Nie korzysta z cudzej bazy, zewnętrznego operatora ani prawdziwych pieniędzy.
