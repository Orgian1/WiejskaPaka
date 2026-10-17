# Etap 11 — projekty rozliczeń prowizji

- Dodano prywatne **projekty** rozliczeń prowizji od wartości towarów (bez opłaty dostawy), tylko dla właściciela zamówienia.
- Stawka jest podawana jawnie w punktach bazowych (10000 = 100%). Reguła: zaokrąglenie half-up do grosza, bez float.
- Dla zamówienia może powstać jeden projekt; ponowna próba zwraca 409.
- Nie są wystawiane faktury, numery faktur, dokumenty VAT ani dokumenty KSeF; nie ma połączenia z zewnętrznym API.
- To **nie** jest rozliczenie należności ani potrącenie pieniędzy. API wymaga autoryzacji rolnika, ale polityka prowizji i fakturowania wymaga jeszcze zatwierdzenia.
- Przed produkcją: zweryfikować status sprzedawców, podstawę prowizji, stawki VAT, podmiot wystawiający, KSeF, faktury korygujące, uprawnienia administratora, idempotencję zewnętrznego API i audyt.
- PostgreSQL: ręcznie zastosować `database/upgrade_11.sql` po upgrade_10.sql; SQLite migruje przy uruchomieniu.
