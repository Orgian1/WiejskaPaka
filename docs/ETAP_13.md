# Etap 13 — wnioski o korekty i audyt księgowy

- `POST /accounting/correction-requests`: rolnik składa wniosek o korektę **projektu** dokumentu; podaje uzasadnienie i proponowaną kwotę netto w groszach.
- `GET /accounting/correction-requests/me`: prywatna lista wniosków.
- `GET /accounting/audit/me`: prywatna historia zgłoszeń.
- Projekty dokumentów są niezmienne; wniosek nie modyfikuje projektu i nie wystawia faktury korygującej.
- PostgreSQL wymaga ręcznego uruchomienia `database/upgrade_13.sql` po poprzednich migracjach.
- Nie ma integracji z KSeF, dostawcą fakturowania ani produkcyjnych płatności.
- Uwaga: przed uruchomieniem księgowości trzeba zweryfikować prawidłowego wystawcę dokumentów, stawki VAT i procedury korekt.
