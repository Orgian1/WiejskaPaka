# WiejskaPaka — pakiet 33–37 (lokalny)

Rozszerzono transakcyjną weryfikację sesji w trybie PostgreSQL na cztery operacje zapisu:
- wylogowanie (`POST /auth/logout`),
- dodawanie produktu (`POST /products`),
- potwierdzanie zasad sprzedawcy (`POST /farmers/me/compliance/acknowledge`),
- przegląd zgodności przez administratora (`POST /admin/farmers/{farmer_id}/compliance/review`).

Każda z nich używa `order_write_db`, który w PostgreSQL weryfikuje token, zgodność identyfikatora i aktualnej roli użytkownika w transakcji zapisu. Tryb SQLite zachowano dla testów lokalnych.

**Ograniczenia:** nie wszystkie operacje zapisu są jeszcze objęte tym mechanizmem. Weryfikacja źródłowa testów nie zastępuje integracyjnych testów z PostgreSQL. RLS nie włączono. Nie modyfikowano bazy Neon ani publicznej witryny. Płatności pozostają testowe.
