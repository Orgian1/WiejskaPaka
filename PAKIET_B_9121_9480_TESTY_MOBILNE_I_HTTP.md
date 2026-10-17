# WiejskaPaka — B/9121–B/9480: kontrola mobilna i akceptacja HTTP

## Wykonane kontrole
- Dodano pięć testów regresyjnych struktury mobilnej (`tests/test_mobile_markup_regression_b9121.py`): obecny dokument HTML, zduplikowane ID, nieistniejący cel kotwicy, zewnętrzny skrypt i brak viewport.
- Kontrola istniejącego HTML: 55 identyfikatorów, 6 kotwic, 3 zasoby, 0 zgłoszonych błędów.
- Testy pytest: 14 zaliczonych (5 nowych oraz 9 istniejących dotyczących dostawy i prywatności).
- Cztery zestawy akceptacyjne lokalnego HTTP: wszystkie zaliczone; szczegóły w `RAPORT_HTTP_AKCEPTACJA_B_9121_9480.json`.
- `node --check web/app.js` oraz `python -m compileall -q backend scripts`: zaliczone.

## Granice weryfikacji
Testy HTTP wykorzystują jednorazową SQLite i symulowane płatności. Kontrola mobilna jest analizą struktury HTML, **nie** testem na fizycznym telefonie. Nie przeprowadzono rzeczywistej integracji PostgreSQL ani testu Chromium przez sieciowe HTTP. Nie zmieniono Neon, domeny, hostingu ani produkcyjnych płatności.
