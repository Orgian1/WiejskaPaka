# B/501–B/520 — wspólna opłata za dostawę (zakres roboczy)

W testowym checkout dla produktów jednego rolnika naliczana jest jedna opłata za dostawę: najwyższa stawka dostawy spośród pozycji koszyka. Jest to zgodne z dotychczasowym mechanizmem orientacyjnej wyceny `/cart/quote`.

Dla zgodności ze schematem, w którym każda pozycja tworzy osobne zamówienie, opłata jest przypisywana wyłącznie do pierwszego zamówienia; pozostałe mają koszt dostawy równy 0. Kwota sumaryczna odpowiada sumie zamówień. Przy późniejszym wprowadzeniu zamówień grupowych należy przeprojektować także rozliczenia, zwroty i dostawy częściowe.

Nie uruchamiano produkcyjnych płatności, nie zmieniano konfiguracji Neon ani domeny. To nie jest kompletne wdrożenie B/501–B/520, tylko jedna spójna poprawka funkcjonalna.
