# Etap 19 — symulacja rozliczeń marketplace

`GET /marketplace/orders/{order_id}/settlement-preview?rate_basis_points=500` jest dostępny tylko rolnikowi będącemu sprzedawcą danego zamówienia (wymaga tokenu). Stawka 500 punktów bazowych = 5%, jest parametrem symulacji, nie zatwierdzoną taryfą. Prowizja naliczana wyłącznie od wartości produktów; koszt dostawy w całości w symulowanej kwocie sprzedawcy. Prowizję obliczamy w groszach według reguł modułu `invoicing.py`. Opłaty operatora płatności nie są uwzględnione.

Endpoint nie zapisuje operacji finansowych, nie pobiera płatności, nie rezerwuje środków i nie zleca wypłat. W przyszłości potrzebne są: operator marketplace z rozdzieleniem środków, idempotentne webhooki z weryfikacją podpisu, księga zdarzeń, zwroty 100% przy winie dostawcy, rozliczenia tygodniowe oraz audyt podatkowy. Nie traktować podglądu jako salda ani dowodu zapłaty.
