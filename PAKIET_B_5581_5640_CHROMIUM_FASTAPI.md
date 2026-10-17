# WiejskaPaka — B/5581–B/5640 — integracja Chromium z FastAPI

Data: 2026-10-15

## Wynik

**ZALICZONY**: `python -m scripts.check_browser_backend_bridge` (kod wyjścia 0).

Test korzysta z prawdziwego Chromium i aplikacji frontendowej, z przekierowaniem wywołań `fetch` do **rzeczywistej aplikacji FastAPI uruchomionej w procesie** przez TestClient. Użyto tymczasowej SQLite; nie testowano połączenia HTTP po sieci, PostgreSQL ani produkcyjnych płatności.

- Rejestracja, logowanie i wylogowanie rolnika oraz klienta.
- Dodanie produktu i punktu odbioru.
- Zakup z odbiorem: 349 groszy.
- Zakup z dostawą: 850 groszy (349 + 501 groszy).
- Anulowanie, ochrona przed ponownym anulowaniem i brak podwójnego przywrócenia stanu.
- Błędne zamówienie bez zmiany magazynu.
- Błędny i poprawny PIN; odmowa ponownego użycia.
- Uprawnienia dostawcy, ukrywanie i cofnięcie dostępu do adresu.
- Niezrealizowana dostawa: testowy zwrot 100% wraz z dostawą i idempotencja.
- Łącznie 86 wywołań API wewnątrz procesu.

## Zdiagnozowany problem

Wcześniejszy test zatrzymywał się na tworzeniu zamówienia: `crypto.randomUUID is not a function` w kontekście `about:blank` używanym przez Playwright. `crypto.randomUUID` wymaga bezpiecznego kontekstu. Dodano wyłącznie w **skrypcie testowym** implementację UUID opartą na `crypto.getRandomValues`, bez zmian w kodzie aplikacji. Test uruchamiać jako moduł z katalogu projektu:

```
python -m scripts.check_browser_backend_bridge
```

## Kontrole dodatkowe

`node --check web/app.js` — zaliczone.
`python -m compileall -q backend scripts` — zaliczone.

## Nadal otwarte

Izolowane testy PostgreSQL, pełna integracja sieciowa HTTP, testy fizycznych urządzeń, pełny audyt bezpieczeństwa i prawny. Neon, hosting, domena i produkcyjne płatności pozostały nietknięte.
