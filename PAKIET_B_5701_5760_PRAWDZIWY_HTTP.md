# WiejskaPaka B/5701–B/5760 — rzeczywisty HTTP localhost

Nowy skrypt `scripts/check_real_http_loopback.py` uruchamia Uvicorn na `127.0.0.1` z jednorazową bazą SQLite, a następnie sprawdza API przez prawdziwe żądania HTTP z biblioteki httpx. Testuje health, katalog, frontend, ochronę prywatnych endpointów, walidację rejestracji, rejestrację klienta i rolnika, logowanie, pobranie profilu, wylogowanie i unieważnienie sesji, a także nagłówki bezpieczeństwa i cache-control.

Wyniki szczegółowe w `HTTP_LOOPBACK_B_5701_5760.json`. To **nie** jest test z przeglądarką Chromium, z PostgreSQL ani na telefonie fizycznym. Nie używa Neon, prawdziwych płatności, hostingu ani domeny. Wymaga dalszych testów produkcyjnych i audytu bezpieczeństwa.

Uruchomienie: `python -m scripts.check_real_http_loopback`.
