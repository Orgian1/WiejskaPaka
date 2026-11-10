# Etap 16 — historia walidacji księgowej

- `POST /accounting/export-jobs/{id}/validate` zapisuje wynik diagnostyki bez ujawniania NIP i danych kontrahentów.
- Ponowna identyczna walidacja jest idempotentna (`UNIQUE(export_job_id,result_sha256)`).
- Zmiana wyniku diagnostyki tworzy nowy wpis w historii.
- `GET /accounting/export-jobs/{id}/validation-history` zwraca maksymalnie 100 ostatnich wyników, tylko właścicielowi.
- Status eksportu pozostaje `blocked_tax_review`; żadne żądanie nie wysyła faktur ani nie kontaktuje się z KSeF.
- PostgreSQL: zastosuj `database/upgrade_16.sql` po wcześniejszych migracjach. Testy integracyjne z działającą bazą nadal wymagane.
- Przed produkcją potrzebny przegląd prawny, podatkowy, bezpieczeństwa oraz testy współbieżności i migracji.
