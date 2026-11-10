# WiejskaPaka B/741–B/760 — administracyjny rejestr przesyłek

Dodano odczytowy endpoint `GET /admin/shipments/overview` dostępny tylko dla roli `admin`.

- Lista przesyłek z liczbą zamówień, wartością produktów, jednorazowym kosztem dostawy, sumą i statusem.
- Stronicowanie `limit` (1–100), `offset` oraz filtr pełnego statusu przesyłki.
- Status `mieszany` w przypadku rozbieżnych statusów zamówień.
- Dla nieudanej dostawy widoczna jest orientacyjna kwota zwrotu **testowego**; nie jest to potwierdzenie rzeczywistego przelewu ani audyt rejestru płatności.
- Bez danych osobowych, adresów, PIN-ów i numerów telefonów.

Testy: `python -m pytest -q tests/test_b741_admin_shipments.py` (1 passed), `python -m pytest -q tests/test_b721_shipment_cancel.py` (1 passed), uruchomione oddzielnie ze względu na osobne testowe bazy i import aplikacji.

Brak zmian konfiguracji Neon, produkcyjnych płatności, domeny i hostingu. Pełna regresja oraz testy PostgreSQL pozostają do wykonania.
