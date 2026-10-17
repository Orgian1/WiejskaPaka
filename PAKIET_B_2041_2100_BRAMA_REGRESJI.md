# B/2041–B/2100: lokalna brama regresji zakupów

## Zmiana
Dodano `scripts/run_checkout_release_gate.py` — powtarzalne uruchamianie dziesięciu kluczowych modułów testów zakupów i przesyłek. Każdy moduł uruchamiany jest w osobnym procesie z osobną bazą SQLite, ponieważ część starszych testów ustawia zmienne środowiskowe i importuje aplikację na poziomie modułu. Uruchomienie wszystkich w jednym procesie może powodować fałszywe błędy wynikające z dzielenia bazy.

## Zakres
Koszyk wielu rolników, jedna opłata za przesyłkę, idempotencja, interfejs zakupowy, równoczesne zakupy, wycena, limity, odbiór PIN, niedostarczenie, anulowania i zwroty testowe.

## Uruchomienie
`python scripts/run_checkout_release_gate.py`

Wyniki są zapisywane do `checkout_release_gate_report.json` (status każdego modułu, czas, końcówka komunikatów). Skrypt zwraca kod różny od zera przy błędzie.

## Ograniczenia
Nie jest to pełna regresja wszystkich modułów, test przeglądarkowy ani test PostgreSQL. Nie podłączano prawdziwych płatności ani Neon. Liczba B/2041–B/2100 to nazwa pakietu, nie liczba zrealizowanych funkcji.
