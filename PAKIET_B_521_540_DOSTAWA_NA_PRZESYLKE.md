# B/521–B/540 — dostawa za przesyłkę (zakres roboczy)

- Wspólny moduł `backend/shipping_policy.py` do naliczania jednej opłaty na przesyłkę sprzedawcy.
- Wycena koszyka pokazuje `shipment_fees_grosze`, rozbite według rolników.
- Checkout korzysta z tej samej reguły; dla kompatybilności ze starszym schematem opłata jest księgowana tylko na pierwszym zamówieniu pozycji w przesyłce.
- Odbiór osobisty: 0 groszy. Kilku sprzedawców: odrębne przesyłki.
- Obecna cena przesyłki jest tymczasowo maksimum ze stawek produktów danego sprzedawcy. Docelowo sprzedawca powinien konfigurować stawkę przesyłki bezpośrednio.
- Nie utworzono jeszcze trwałej encji `shipments` ani osobnego PIN dla całej przesyłki: nadal istnieją zamówienia na każdą pozycję. To wymaga migracji i przebudowy potwierdzeń odbioru.
- Nie wykonano integracji z Neon ani rzeczywistych płatności.
