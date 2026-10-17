# Etap 17 — potwierdzenie przeglądu diagnostyki

- `POST /accounting/export-jobs/{id}/acknowledge-validation`: rolnik potwierdza zapoznanie się z **najnowszym zapisanym wynikiem walidacji**. Operacja jest idempotentna.
- `GET /accounting/export-jobs/{id}/review-status`: status potwierdzenia najnowszej walidacji.
- Nowy wynik kontroli automatycznie powoduje, że status potwierdzenia najnowszego wyniku jest ponownie `false`.
- Potwierdzenie **nie jest zatwierdzeniem podatkowym**, nie usuwa błędów, nie zmienia statusu zadania, nie wysyła do KSeF i nie wystawia faktur.
- PostgreSQL: po migracjach 01–16 uruchomić `database/upgrade_17.sql`. Testy na realnej instancji PostgreSQL są nadal wymagane.
