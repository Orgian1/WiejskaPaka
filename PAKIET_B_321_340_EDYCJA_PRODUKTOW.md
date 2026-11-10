# WiejskaPaka — pakiet B/321–B/340 (zakres roboczy)

Wdrożona funkcja: PATCH /products/mine/{product_id} — edycja własnej oferty przez rolnika.

- Obsługa częściowej aktualizacji nazwy, ceny, kosztu dostawy i stanu magazynowego.
- Weryfikacja roli i sesji przy zapisie; warunek farmer_id w samym UPDATE.
- Zwracanie 404 dla nieistniejącego lub cudzego produktu.
- Odrzucenie pustego żądania, jawnych wartości null i kwot spoza limitów.
- Stan magazynowy jest wartością bezwzględną; zmiany równoległe wymagają dalszych testów integracyjnych.
- Kwoty nadal wyrażone w groszach; brak rzeczywistych płatności.

Testy: 13 zaliczonych w wybranym zestawie (6 nowych). Nie oznacza to pełnej regresji.
Nie testowano integracji z rzeczywistą bazą Neon.
