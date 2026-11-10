# Pierwotne warunki zakupu testowego

Nowe zakupy pojedyncze oraz z koszyka tworzą w tej samej transakcji zapis
`order_purchase_records`. Błąd zapisu wycofuje zamówienie, przesyłkę, rezerwację,
zmianę stanu magazynu i opróżnienie koszyka. Ponowienie z tym samym kluczem
idempotencji zwraca poprzedni zakup, bez drugiego zapisu.

## Co pozostaje z chwili zakupu

Nazwa produktu, cena jednostkowa, ilość, kwoty produktów/dostawy/razem,
rodzaj realizacji, publiczny kod paczki, czas zakupu, czas zapisu i początkowy
termin rezerwacji. Przy odbiorze: ID, nazwa, adres, godziny i opcjonalne
współrzędne punktu. Zmiana katalogu lub punktu po zakończeniu zamówienia
nie zmienia tych danych. Przedłużenie lub zmiana bieżącej rezerwacji nie
przepisuje pierwotnego terminu. Wszystkie kwoty są całkowitymi groszami.

Nie kopiujemy adresu dostawy klienta, PIN-u, telefonu, hasła ani tokenu.
Identyfikatory stron służą autoryzacji; nie są dodawane do eksportowanego
obiektu warunków. Dostęp do adresów dostawy pozostaje w istniejącym,
odrębnym mechanizmie ograniczonym do realizacji przesyłki.

## Dostęp i interfejs

- `GET /orders/{order_id}/purchase-record`: wyłącznie kupujący i rolnik
  będący stronami zamówienia.
- `GET /shipments/{shipment_id}/purchase-record`: te same zasady dla całej
  przesyłki. Suma dostawy obejmuje najwyżej jedną dodatnią opłatę i musi
  odpowiadać przesyłce. Odbiór wymaga tego samego pierwotnego punktu dla pozycji.
- Obce konto otrzymuje 404; dostawca i administrator nie dostają tego podglądu.
  Brak uwierzytelnienia daje 401. Odpowiedzi są `no-store`.
  Sesja i rola są sprawdzane ponownie w transakcji odczytu, również w SQLite.
- Karty zamówień i przesyłek klienta/rolnika zawierają przyciski podglądu
  oraz pobrania JSON. Opóźniona odpowiedź po wylogowaniu, zmianie konta,
  usunięciu karty lub nowszym żądaniu nie renderuje ani nie pobiera danych.
- `GET /admin/orders/purchase-record-audit`: administrator otrzymuje kontrolę
  zgodności i kompletności z ID oraz kodami problemów, bez nazw, adresów i PIN-ów.
  Audyt niczego nie naprawia ani nie dopisuje.

Oddzielamy pierwotne warunki od aktualnego stanu płatności testowej, odbioru
oraz zwrotu. Zwrot nie zmienia pierwotnej ceny. Niezgodność identyfikatorów,
kwot, daty lub powiązania z punktem powoduje 409 i wymaga weryfikacji.

## Migracja i ograniczenia

SQLite instaluje tabelę i trzy triggery blokujące UPDATE, DELETE oraz
zastępowanie istniejącego rekordu przez INSERT OR REPLACE. PostgreSQL wymaga
jawnej migracji `database/upgrade_b10921_purchase_records.sql`; rola aplikacji
nie tworzy schematu. Trigger PostgreSQL blokuje UPDATE i DELETE, klucz
pierwotny blokuje duplikaty. Natywny test z ograniczoną rolą jest dostarczony,
ale nie został uruchomiony w tej sesji z powodu braku działającego serwera.

**Brak wstecznego uzupełniania:** dla starych zamówień bez zapisu API zwraca
`original_available: false` i `original: null`. Nie udajemy, że obecna oferta
lub obecny adres są warunkami dawnego zakupu. W mieszanej przesyłce można
odczytać dostępne pozycje, ale nie otrzymuje ona zgadywanej sumy pierwotnej.
Audyt osobno podaje brakujące rekordy oraz niespójności istniejących danych.

Jest to zapis demonstracyjny: bez faktury, kwalifikowanego podpisu i dowodu
rzeczywistej płatności. Kontrole bazy nie chronią przed jej administratorem
usuwającym triggery. Nie stanowią niezależnego audytu ani ukończonej polityki
retencji. Kontrolowana anonimizacja/usuwanie danych i wymagane okresy
przechowywania wymagają projektu przed produkcją; zwykły DELETE jest blokowany.
Prawa konsumenta pozostają zachowane, a PIN ich nie ogranicza.

## Odtworzenie testów

```bash
.venv/bin/python scripts/run_tests_per_file.py --report moje_testy_historii.json test_purchase_records.py test_purchase_records_ui.py test_purchase_records_http.py test_purchase_record_http_restart.py
.venv/bin/python scripts/check_purchase_records_http.py --report moje_http_historii.json
```

Testy JavaScript uruchamia Node w kontrolowanym DOM. To nie jest Chromium.
Test HTTP uruchamia rzeczywisty serwer Uvicorn na loopback i jednorazową SQLite.
