# WiejskaPaka — B/66–B/70: izolacja kont

Pięć testów integracyjnych na FastAPI i lokalnej bazie SQLite:

- B/66: rolnik nie widzi zamówień innego rolnika.
- B/67: klient nie widzi zamówień innego klienta.
- B/68: obcy klient nie pobiera lokalizacji zamówienia.
- B/69: nieprzypisany kurier nie widzi adresu, historii ani zamówienia.
- B/70: obcy rolnik nie może podejrzeć historii ani potwierdzić zamówienia.

Testy używają odrębnych kont i prawdziwych endpointów FastAPI; nie łączą się z Neon ani z publiczną witryną. Nie dowodzą poprawności PostgreSQL/RLS. Do uruchomienia: `python -m pytest -q tests/test_cross_account_isolation_b66_b70.py`.
