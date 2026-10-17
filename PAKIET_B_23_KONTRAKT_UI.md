# WiejskaPaka — pakiet B/23: kontrola struktury interfejsu

- Trzy nowe testy w `tests/test_ui_dom_contract.py` analizują **faktycznie serwowany** plik `web/index.html`, nie osobny prototyp marketingowy.
- Kontrola unikatowych identyfikatorów HTML i celów wszystkich lokalnych odnośników nawigacji.
- Kontrola, że panele prywatne są ukryte w początkowym HTML (nie zastępuje autoryzacji serwera).
- Kontrola istnienia lokalnych skryptów i arkusza CSS.
- Test Chromium wyświetla jednoznaczny komunikat, jeśli środowisko blokuje localhost; **nie oznacza takiej próby jako zaliczonej**.

Nie przeprowadzono testu wizualnego na telefonie ani testu na prawdziwym PostgreSQL. Neon, domena i płatności bez zmian.
