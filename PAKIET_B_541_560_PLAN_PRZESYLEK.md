# WiejskaPaka — B/541–B/560: planowanie przesyłek (moduł przygotowawczy)

Dodano `backend/shipment_groups.py` z funkcją `build_shipment_plan`.
Grupowanie po rolniku i identyfikatorze przesyłki. Jeden koszt dostawy na przesyłkę niezależnie od liczby pozycji. Odbiór osobisty: 0 groszy. Kwoty całkowite w groszach, kontrola przepełnienia BIGINT. Obecna stawka jest wyznaczana jako maksymalna stawka produktu w grupie — tymczasowa polityka z poprzednich pakietów, do zastąpienia taryfą ustalaną przez sprzedawcę dla przesyłki.

Testy: 11 zaliczonych (`pytest -q tests/test_shipment_groups.py`).

**Ograniczenie:** moduł planowania NIE jest jeszcze podłączony do checkout ani bazy danych. Brak trwałego identyfikatora przesyłki i jednego PIN-u dla całej grupy. Dotychczasowy checkout nadal tworzy osobne zamówienia na pozycję i rozdziela wspólną opłatę w ich zapisach. Nie wykonano testów integracyjnych z Neon. Nie podłączono płatności rzeczywistych.

Następne prace: migracja `shipments` + `shipment_items`, integracja checkout i operacji potwierdzania odbioru z jedną przesyłką, izolacja testów i testy integracyjne.
