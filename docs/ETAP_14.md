# Etap 14 — kolejka przygotowania eksportu księgowego

Dodano prywatny podgląd danych dokumentu (`GET /accounting/export-preview/{draft_id}`), idempotentne utworzenie blokowanego zadania (`POST /accounting/export-jobs/{draft_id}`) i listę zadań (`GET /accounting/export-jobs/me`). Wszystkie wymagają sesji rolnika i kontroli własności projektu. W podglądzie nie ma NIP-ów ani danych kontrahentów.

Zadania mają **wyłącznie** status `blocked_tax_review`. Nie są wykonywane w tle, nie wysyłają danych przez HTTP, nie tworzą faktur, korekt, numerów faktur ani zgłoszeń KSeF. Przed przyszłym uruchomieniem integracji trzeba zweryfikować wystawcę, podstawę opodatkowania, stawkę VAT, wymagane dane kontrahenta, zgodność z KSeF i uprawnienia API. Osobna usługa będzie wymagać bezpiecznego przechowywania sekretów, idempotencji po stronie dostawcy, retry/backoff, audytu i mechanizmu uzgadniania statusów.

SQLite migruje automatycznie przy uruchomieniu; PostgreSQL wymaga zastosowania `database/upgrade_14.sql` **po** `upgrade_13.sql`. Testy lokalne nie zastępują testów na prawdziwym PostgreSQL.
