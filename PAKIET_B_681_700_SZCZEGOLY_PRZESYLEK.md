# B/681–B/700 — szczegóły przesyłek i kontrola dostępu

Nowy endpoint `GET /shipments/{shipment_id}/details` udostępnia właścicielowi przesyłki (klient), rolnikowi sprzedającemu i przypisanemu do **wszystkich** zamówień dostawcy podsumowanie przesyłki oraz pozycje z ich statusami. Nie ujawnia adresu, numerów telefonów ani PIN-u. Kwota zwrotu w trybie testowym dostępna jest klientowi i rolnikowi, nie dostawcy.

Wszystkie kwoty są w groszach. Koszt dostawy jest naliczany raz na przesyłkę. Endpoint tylko odczytuje dane, nie uruchamia zwrotu. Nie zmieniono konfiguracji Neon ani produkcyjnych płatności.

Testy: `python -m pytest -q tests/test_b681_shipment_details.py tests/test_b641_shipment_failure.py tests/test_b621_courier_shipments.py` — 3 zaliczone. Nie przeprowadzono pełnej regresji.
