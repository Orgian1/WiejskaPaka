# WiejskaPaka B/841–B/900 — audyt przesyłek (zakres roboczy)

- Dodano tylko do odczytu `GET /admin/shipments/{shipment_id}/audit`: chronologiczne zdarzenia zamówień, rzeczywiste wartości zwrotów z testowego rejestru płatności i kontrolę zgodności kosztu dostawy.
- W `GET /admin/shipments/overview` kwota zwrotu jest odczytywana z testowego rejestru, a nie szacowana na podstawie statusu.
- Brak ujawniania adresów, PIN-ów i numerów telefonów; dostęp tylko dla administratora.
- Nie zmieniono Neon, hostingu ani rzeczywistych płatności.
- Numeracja pakietu oznacza zakres roboczy, nie 60 ukończonych funkcji.
