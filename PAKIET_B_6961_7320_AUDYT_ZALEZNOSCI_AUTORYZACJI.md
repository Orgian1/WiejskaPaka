# WiejskaPaka B/6961–B/7320 — audyt strukturalny autoryzacji

## Wykonano
- Nowy skrypt `scripts/audit_route_auth_dependencies.py` analizuje zależności FastAPI wszystkich 87 kombinacji metod i tras API.
- Raport `RAPORT_ZALEZNOSCI_AUTORYZACJI_B_6961_7320.json` zawiera zależności, kandydatów tras publicznych i pola do ręcznego przeglądu.
- W tym zestawie wszystkie trasy nieoznaczone jako publiczne mają bezpośrednią zależność `current_user`. To tylko kontrola strukturalna, **nie** dowód poprawnych uprawnień do poszczególnych rekordów.
- Nowe testy sprawdzają pokrycie i brak nieoznaczonych tras bez zależności.

## Zweryfikowano
- 6/6 testów pytest (3 nowe, 3 istniejące).
- `node --check web/app.js` i `python -m compileall -q backend scripts` bez błędów.

## Nadal wymagane
- Ręczna i dynamiczna kontrola autoryzacji obiektowej oraz uprawnień każdej roli.
- Integracja z izolowanym PostgreSQL, test Chromium z HTTP, fizyczne telefony, audyt prawny.
- Brak połączeń z Neon i produkcyjnymi płatnościami.
