# Zgłoszenia problemów z zakupem — wersja testowa

Uruchom `python scripts/run_phone_demo.py --sample-data`. Wszystkie wpisy
muszą być fikcyjne. Panel działa tylko przy jawnie włączonym trybie testowych
operacji `WP_ENABLE_TEST_PAYMENTS=1`. Nie wykonuje rzeczywistej komunikacji,
zwrotu ani rozstrzygnięcia prawnego.

## Scenariusz trzech ról

1. Jako klient otwórz panel zakupów i przy przesyłce albo zamówieniu wybierz
   „Zgłoś problem z zakupem (TEST)”. Wybierz kategorię i wpisz 10–2000 znaków.
   Nie wpisuj PIN-u, hasła, telefonu ani danych dokumentów.
2. W sekcji „Zgłoszenia problemów — TEST” odśwież listę i otwórz sprawę.
   Opis widzą kupujący, sprzedawca tego zakupu i administrator. Dostawca
   oraz konta innych klientów i sprzedawców nie mają dostępu.
3. Wyloguj się i zaloguj rolnika. Odśwież zgłoszenia, otwórz sprawę i zapisz
   fikcyjną odpowiedź. Wpis pojawi się w historii kupującego i administratora.
4. Jako administrator zapisz odpowiedź ze stanem „W obsłudze” lub
   „Zamknięte testowo”. Do zmiany stanu potrzebny jest wpis z uzasadnieniem.
   Zamkniętą sprawę może ponownie otworzyć administrator, wybierając
   „W obsłudze / otwórz ponownie”. Klient i rolnik nie zmieniają tego stanu.
5. Jako klient sprawdź historię i zamknięty stan. Zamknięcie usuwa formularz
   odpowiedzi, ale nie usuwa historii. Wylogowanie czyści widok i szkice.
   Odświeżanie historii również usuwa niezapisany szkic odpowiedzi.

Produkt należący do przesyłki jest automatycznie powiązany ze sprawą całej
przesyłki. Osobne zamówienie pozostaje osobnym zamówieniem. Zgłoszenie nie
jest operacją częściowego odbioru ani częściowego zwrotu.

## Zakres i ograniczenia

- Kategorie: produkt, odbiór w punkcie, dostawa, inny problem.
- Stan początkowy: nowe. Odpowiedź ma 1–2000 znaków. Historia zawiera role
  autorów i daty, bez adresów kont, adresu dostawy i PIN-ów pobieranych
  z zamówienia. Swobodnie wpisana treść nie jest automatycznie anonimizowana.
- Tworzenie, odpowiadanie i zamykanie nie zmienia stanu zamówienia,
  magazynu, płatności ani rozliczeń. Osobne przyciski anulowania lub zwrotu
  zachowują własne warunki. Sam wpis nie uruchamia żadnego z nich.
- Nie ma załączników, realnej wysyłki e-mail ani SMS. Uczestnicy jawnie
  odświeżają sekcję zgłoszeń. Nie dodano automatycznych decyzji lub terminów.
- To testowy przepływ obsługi problemu, nie kompletna produkcyjna procedura
  reklamacji. Docelowy proces, terminy, komunikacja i retencja wymagają
  ustalenia przed uruchomieniem rzeczywistej sprzedaży.
- Treść zapisuje się w lokalnej bazie demo. Wchodzi do kopii całej bazy;
  reguły ochrony kopii opisano w `ODTWARZANIE_SQLITE.md`. Nie wpisuj
  rzeczywistych danych do jednorazowego demo ani jego raportów.

## Kontrakt API

| Operacja | Ścieżka |
| --- | --- |
| Lista własnych spraw / kolejka administratora | `GET /test/support/cases` |
| Utworzenie przez kupującego | `POST /test/support/cases` |
| Szczegóły i strona historii | `GET /test/support/cases/{id}` |
| Odpowiedź / administracyjna zmiana stanu | `POST /test/support/cases/{id}/replies` |

Tworzenie przyjmuje `kind` (`order` lub `shipment`), tekstowy `target_id`,
`category` (`product`, `pickup`, `delivery`, `other`), `description` i UUID
`request_id`. Identyfikator jest przypisany do kupującego. Ponowienie
identycznej operacji zwraca tę samą sprawę; inne dane z tym samym kluczem
powodują 409. W PostgreSQL operacje tego samego kupującego są serializowane.

Odpowiedź przyjmuje `message`, UUID `request_id`, całkowitą dodatnią
`expected_revision` oraz opcjonalny `status` (`in_review` lub `closed_test`)
wyłącznie dla administratora. Identyfikator ponowienia jest związany ze
sprawą i autorem. Identyczna odpowiedź nie dodaje drugiego wpisu nawet przy
starej wersji; zmieniona treść z tym samym kluczem daje 409. Inny nowy wpis
ze starej wersji daje 409 i wymaga odświeżenia. PostgreSQL blokuje sprawę,
a SQLite używa istniejącej transakcji BEGIN IMMEDIATE. Autoryzacja zapisu
jest ponownie sprawdzana wewnątrz tej transakcji.

Lista obsługuje `status`, `limit` 1–50 (domyślnie 20), `offset` 0–10000.
Nie zawiera treści zgłoszeń. Szczegóły zwracają do 20 wpisów w kolejności
wersji. `before_revision` pobiera wcześniejszą stronę; UI udostępnia
„Pokaż wcześniejsze wpisy”. Wersja liczona całkowicie zastępuje datę zegara
przy ochronie przed równoczesnym zapisem.

SQLite tworzy dwie tabele podczas inicjalizacji aplikacji. PostgreSQL wymaga
`upgrade_z_support_cases_test.sql`, dodanego do przeglądanego manifestu
nowej izolowanej bazy i blokady sum kontrolnych. Przy włączonej funkcji brak
tabel blokuje start, zamiast udawać dostępność panelu. Nie wykonano migracji
żadnej zewnętrznej bazy.
