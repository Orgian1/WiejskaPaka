# Pakiet B/26 — prywatność odpowiedzi HTTP

Zmiana w `backend/app.py`: nagłówek `Cache-Control: no-store` jest teraz regułą domyślną dla wszystkich tras poza jawnie wskazanymi publicznymi odpowiedziami GET/HEAD (`/`, `/health`, `/products`, `/marketplace/accounting-policy`, `/assets/*`). Dodatkowo odpowiedzi niepubliczne otrzymują `Pragma: no-cache`.

Uzasadnienie: poprzednia lista prefiksów nie obejmowała np. `/admin/...`, `/pickup-points`, i potencjalnych nowych endpointów. Nowe prywatne trasy są teraz chronione domyślnie.

Dwa dodatkowe testy w `tests/test_private_cache_headers.py` weryfikują ścieżki administratora, operacje zmieniające dane oraz podobne nazwy ścieżek.

Testy lokalne: 2480 passed, 6 skipped, 16 subtests passed. Testy PostgreSQL i wizualne Chromium nie zostały wykonane. Zmiany nie wymagają połączenia z Neon, płatnościami ani publiczną stroną.
