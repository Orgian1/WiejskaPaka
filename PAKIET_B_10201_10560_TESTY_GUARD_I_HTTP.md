# WiejskaPaka — pakiet B/10201–B/10560

## Wykonane kontrole

- Nowy plik `tests/test_b10201_postgres_guard_adversarial.py`: **24 testy zaliczone**. Testy sprawdzają blokadę niebezpiecznych lub niejednoznacznych adresów PostgreSQL, wymóg wyraźnej zgody na zdalną bazę testową oraz konserwatywne zachowanie bramki wdrożeniowej. Testy nie otwierają połączenia z bazą.
- `python scripts/run_http_acceptance_suite.py`: **4/4 zestawy zaliczone** (lokalny HTTP, zakup–dostawa–zwrot, koszyk wielu rolników, prywatność i dostawa). Wykorzystują lokalną bazę SQLite i symulowane płatności.
- `python -m compileall -q backend scripts`: PASS.
- `node --check web/app.js`: PASS.
- `python -m scripts.release_gate`: kod 2, **prawidłowo blokuje produkcyjne wdrożenie** przy braku ośmiu wymaganych dowodów. Nie interpretować tego jako usterki.

## Ograniczenia

- Nie uruchomiono rzeczywistej instancji PostgreSQL; brak serwera i sterownika w tym środowisku. Neon nietknięty.
- Nie uruchomiono przeglądarki Chromium przez sieciowe HTTP ani testów na fizycznych telefonach.
- Bramka produkcyjna pozostaje zamknięta. Nie podłączono prawdziwych płatności, domeny ani hostingu.
- Numeracja pakietu oznacza zakres organizacyjny, a nie liczbę zmian czy testów.
