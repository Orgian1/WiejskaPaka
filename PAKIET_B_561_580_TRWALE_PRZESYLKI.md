# B/561–B/580: trwałe grupowanie zamówień w przesyłki (zakres roboczy)

- Dodano `shipment_groups` oraz `shipment_order_links` dla SQLite i osobną migrację PostgreSQL.
- Checkout testowy tworzy jeden identyfikator przesyłki na zakup u jednego rolnika i wiąże z nim wszystkie wiersze zamówień atomowo.
- Koszt dostawy naliczany jest raz dla przesyłki, zgodnie z wcześniejszą regułą.
- `GET /shipments/mine` zwraca wyłącznie przesyłki zalogowanego klienta.
- Migrację PostgreSQL należy wykonać ręcznie po kopii zapasowej, przed użyciem zmodyfikowanego checkoutu.
- Ograniczenia: dotychczasowe zamówienia nie mają automatycznego backfillu; potwierdzanie PIN nadal działa na poziomie pojedynczego zamówienia. Nie należy jeszcze przedstawiać go jako jednego PIN-u dla całej przesyłki.
- Testy uruchamiać osobno: starsze zestawy korzystają z globalnej bazy przy imporcie i mają znany problem izolacji.
- Brak prawdziwych płatności, domeny i zmian w produkcyjnym Neon.
