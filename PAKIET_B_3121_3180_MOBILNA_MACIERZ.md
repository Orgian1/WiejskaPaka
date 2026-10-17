# B/3121–B/3180 — rozszerzona kontrola mobilna

- Rozszerzono skrypt `scripts/check_mobile_browser.py` o pięć rozdzielczości: 320, 360, 390, 768 i 1280 px.
- Dla małych ekranów włączono emulację dotyku i urządzenia mobilnego.
- Dodano wykrywanie nieudanych żądań sieciowych, kontrolę przepełnienia zarówno `body`, jak i `documentElement`, oraz kontrolę polskiej wersji językowej i meta viewport.
- Dodano trzy testy jednostkowe macierzy mobilnej.
- Uruchomiono `python -m pytest -q tests/test_b3121_mobile_viewport_matrix.py tests/test_mobile_browser_runner.py`: **6 passed**.
- Uruchomiono skrypt Chromium: środowisko zablokowało dostęp Chromium do localhost (`ERR_BLOCKED_BY_ADMINISTRATOR`). **Nie zaliczono rzeczywistego testu przeglądarkowego**.
- Żadnych zmian w Neon, produkcyjnych płatnościach, hostingu ani domenie.
