# WiejskaPaka — B/46–B/50: dostawcy i zwroty testowe

Rozbudowano `scripts/check_browser_backend_bridge.py` o scenariusze wykonywane na jednorazowej SQLite i prawdziwych endpointach FastAPI przez `TestClient` (bez połączenia HTTP). Wykonywany jest również Chromium dla istniejących scenariuszy UI.

- B/46: niezalogowany do zamówienia dostawca nie widzi adresu klienta.
- B/47: tylko rolnik może przypisać dostawcę; ponowny przydział jest odrzucany; sam przydział nie ujawnia adresu.
- B/48: adres jest dostępny jedynie przypisanemu dostawcy podczas aktywnej dostawy; inny dostawca i rolnik nie otrzymują adresu.
- B/49: zły PIN pomniejsza liczbę prób, poprawny PIN kończy dostawę, a adres znika z dostępnych lokalizacji.
- B/50: symulowane niepowodzenie dostawy po symulowanej płatności powoduje testowy zwrot całej kwoty 850 groszy (349 groszy produkt + 501 groszy dostawa); powtórzenie zdarzenia o tym samym identyfikatorze nie zwiększa zwrotu.

Uruchomienie: `python -m scripts.check_browser_backend_bridge` w katalogu projektu, wymagane Chromium i Playwright.

**Ograniczenia:** Nie wykonano prawdziwego przelewu ani zwrotu. B/50 testuje wyłącznie księgowy stan symulatora, a nie zmianę statusu dostawy na produkcji. Scenariusze kuriera w tej paczce używają API przez TestClient, nie panelu kuriera w Chromium. Nie przetestowano PostgreSQL, RLS, normalnego połączenia HTTP ani fizycznego telefonu. Nie dotykano Neon ani wiejskapaka.pl.
