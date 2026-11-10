# Ilości ułamkowe: wycena testowa

Dodano uwierzytelniony endpoint klienta POST /cart/quote-quantities-test.
Wymaga obu flag: WP_ENABLE_PRODUCT_UNITS=1 i WP_ENABLE_FRACTIONAL_QUOTE=1.
Domyślnie jest wyłączony. Nie ma jeszcze formularza zakupu ułamków.

Przykładowe dane wejściowe:

```json
{"items":[{"product_id":1,"quantity_text":"0,5"}],"fulfillment":"dostawa"}
```

Ilość musi być tekstem dziesiętnym (przecinek lub kropka). Kg i litry
mają dokładność 0,001, pozostałe jednostki pozostają niepodzielne.
Cena jest za jednostkę sprzedaży. Zawartość worka/butelki nie zmienia
liczby kupowanych opakowań. Kwoty są całkowitymi groszami; half-up po
mnożeniu całej pozycji. Linia zaokrąglona do zera jest odrzucana.

Odpowiedź jawnie zawiera contract=sale-quantity-quote-v1,
checkout_supported=false, inventory_reserved=false oraz indicative=true.
Nie zapisuje koszyka, nie rezerwuje magazynu, nie tworzy zamówień ani płatności.
Jeden sprzedawca/przesyłka: jedna opłata dostawy zgodna z obecną polityką.
Oddzielne przesyłki mają osobne, widoczne opłaty. Odbiór bez tej opłaty.

Istniejące products.stock i orders.quantity nadal oznaczają całe jednostki
sprzedaży. Wycena przelicza stock na jednostki bazowe tylko w pamięci.
Nie przepisuje go jako gramów ani nie modyfikuje historycznych zamówień.
Dotychczasowy checkout i zapisany koszyk nadal odrzucają ułamki.
Konfiguracja /product-units rozróżnia fractional_quote_enabled od
fractional_quantities=false, aby nie reklamować gotowego zakupu ułamków.

## Weryfikacja i dalsza praca

39 testów lokalnych zaliczonych (obliczenia, HTTP, stary koszyk i kontrole
autoryzacji). Użyto requirements-lock.txt, Python 3.12.14, izolacja per moduł.
Dowody: docs/audits/fractional_quote_2026-10-21/focused.json.
Nie jest to pełna regresja tej nowej wersji ani test jej endpointu na PostgreSQL.

Do pełnego zakupu pozostają: wersjonowany zapis ilości w bazie, atomowe
rezerwacje/zwolnienia, idempotencja checkoutu, niezmienny zapis ceny i ilości
zamówienia, sumy przesyłek, integracja UI oraz testy anulowań i restartów.
Nie włączać formularza zakupowego ułamków przed wspólną integracją tych ścieżek.
Nie wykonywano zmian na VPS ani migracji istniejących danych.
