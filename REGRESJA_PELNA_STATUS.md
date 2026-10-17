# WiejskaPaka — próba pełnej regresji (15.10.2026)

## Zakres
- Wykryto **2805 testów** (`python -m pytest --collect-only -q`).
- Uruchomiono pełną regresję `python -m pytest -q`, ale przebieg przekroczył limit wykonania i został przerwany; do tego momentu pojawiły się niezaliczone testy.
- Uruchomiono również regresję per plik, ale również nie zakończyła się w dostępnym limicie czasu. Szczegóły zapisano w `REGRESJA_WYNIKI.json` (wyłącznie ukończone moduły).
- W częściowej regresji per plik: 20 modułów PASS, 3 TIMEOUT, 1 FAIL. FAIL w `test_b1861_quote_ui_contract.py` był wynikiem przestarzałego sprawdzenia dosłownego tekstu funkcji `logged(user)` po dodaniu `checkoutOwner`; poprawiono test i ponowne uruchomienie dało 2 PASS.
- `node --check web/app.js` i `python -m compileall -q backend`: PASS.

## Wniosek
**Nie można potwierdzić przejścia całej regresji**. Testy przekraczające czas wykonania wymagają izolacji, szczególnie moduły uruchamiające zagnieżdżone procesy pytest. Nie wolno oznaczać projektu jako w pełni przetestowanego ani gotowego do wdrożenia.

## Następny krok
Uruchomić testy w kontrolowanych porcjach bez zagnieżdżania pełnych przebiegów, z osobnymi limitami czasu i raportem niezaliczonych przypadków. Następnie wykonać testy PostgreSQL, przeglądarkowe i mobilne.
