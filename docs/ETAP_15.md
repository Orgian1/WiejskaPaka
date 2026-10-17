# Etap 15 — diagnostyka błędów kolejki księgowej

Nowy endpoint `GET /accounting/export-jobs/{job_id}/diagnostics` dostępny tylko właścicielowi projektu (rola rolnik). Zwraca flagę zgodności SHA-256 deterministycznego podglądu, liczbę wniosków o korektę oczekujących na przegląd oraz kody problemów: `snapshot_changed`, `pending_correction_review`, `amount_mismatch`, `negative_amount`, `tax_review_required`.

**Zawsze** `ready_for_external_api=false`. Nie uruchomiono adaptera API, prób wysyłki, retry, wystawiania faktur ani KSeF. Funkcja służy wyłącznie diagnostyce lokalnej. Nie zawiera danych osobowych i nie zmienia dokumentów. Brak zmian schematu SQL.

Testy: `python -m pytest -q tests`.
