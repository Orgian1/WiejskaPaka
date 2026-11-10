# WiejskaPaka B/3061–B/3120 — Chromium i kontrola UI

## Wykonano
- Uruchomiono prawdziwą przeglądarkę Chromium z interfejsem aplikacji oraz mostkiem do rzeczywistego FastAPI TestClient na jednorazowej bazie SQLite.
- Scenariusz integracyjny zaliczył: rejestrację, logowanie, tworzenie produktów i punktu odbioru, zakup, anulowanie, PIN, dostawcę, prywatność adresu, niedostarczenie i pełny zwrot testowy. 86 żądań API.
- Wykryto nieaktualne założenie w skrypcie przeglądarkowym: nawigacja zawiera pięć, a nie cztery linki. Poprawiono skrypt i jego test kontraktowy.
- Dziesięć wybranych testów narzędzi przeglądarkowych zaliczonych.

## Ograniczenia
- Test z prawdziwą siecią localhost (`python -m scripts.check_mobile_browser`) NIE przeszedł: środowisko blokuje dostęp Chromium do localhost (`ERR_BLOCKED_BY_ADMINISTRATOR`). Nie jest to dowód błędu aplikacji.
- Mostek Chromium ↔ FastAPI działa w procesie testowym, nie zastępuje testów wdrożenia HTTP, rzeczywistego telefonu ani PostgreSQL.
- Nie uruchamiano płatności produkcyjnych; Neon i domena bez zmian.

## Uruchomienie
```
python -m scripts.check_browser_backend_bridge
python -m pytest -q tests/test_browser_navigation_contract_b25.py tests/test_mobile_browser_runner.py tests/test_browser_screenshot_option_b28.py tests/test_browser_backend_bridge.py
python -m scripts.check_mobile_browser
```
