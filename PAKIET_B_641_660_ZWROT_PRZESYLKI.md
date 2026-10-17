# WiejskaPaka B/641–B/660 — nieudana dostawa całej przesyłki (tryb testowy)

Dodano POST `/shipments/{shipment_id}/courier-failure-test` dla właściciela gospodarstwa. Wymaga `WP_ENABLE_TEST_PAYMENTS=1`, powodu `dostawca_nie_przyjechal` albo `dostawca_nie_dostarczyl`, przesyłki w całości w drodze i symulowanej opłaty każdego zamówienia.

W jednej transakcji następuje pełny zwrot symulowany za WSZYSTKIE pozycje (w tym opłata za przesyłkę naliczona tylko raz), zmiana wszystkich statusów, dziennik zdarzeń i zablokowanie potwierdzenia PIN-em. Ponowne wywołanie dla już zwróconej przesyłki nie nalicza zwrotu drugi raz. Błędy walidacji cofają całą transakcję.

**Ograniczenia:** To nie jest prawdziwy zwrot bankowy ani potwierdzenie faktycznej płatności. Rolnik zgłasza przyczynę; brak niezależnego potwierdzenia od kuriera i procedury rozstrzygania sporów. Nie wykonano pełnej regresji ani testów PostgreSQL/Neon. Nie zmieniano zdalnej bazy.
