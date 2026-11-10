# Etap 12 — projekty faktur (bez wystawiania)

- Endpoint POST /accounting/invoice-drafts tworzy prywatny, niezmienny szkic na podstawie projektu prowizji.
- GET /accounting/invoice-drafts/me udostępnia szkice wyłącznie właścicielowi projektu rozliczenia.
- Kwota prowizji jest w groszach; VAT i brutto są celowo NULL, dopóki nie zostanie ustalony prawidłowy wystawca, status podatkowy i stawka.
- Nie są nadawane numery faktur, nie jest generowany dokument podatkowy ani wykonywane wywołania do KSeF.
- Dane `seller_*` i `buyer_*` są wyłącznie propozycjami wprowadzanymi przez użytkownika, bez urzędowej weryfikacji. Przed prawdziwym wystawianiem konieczna kontrola prawna, podatkowa i model uprawnień platformy.
- Przed produkcją: odrębny workflow księgowy z uprawnieniami wystawcy, numeracją, idempotentnym adapterem dostawcy, kolejką retry, webhookami, korektami, audytem i KSeF.
- PostgreSQL: uruchom upgrade_12.sql po upgrade_11.sql. Integracyjne testy PostgreSQL nadal oczekują.
