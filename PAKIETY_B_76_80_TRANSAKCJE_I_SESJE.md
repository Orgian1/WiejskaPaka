# WiejskaPaka — B/76–B/80: transakcje i sesje

Pięć nowych testów integracyjnych `tests/test_transaction_safety_b76_b80.py`:

- B/76: błędny punkt odbioru nie zmniejsza stanu magazynu ani nie tworzy zamówienia.
- B/77: niekompletny adres dostawy nie tworzy zamówienia.
- B/78: po odrzuconym zakupie następny poprawny zakup nadal działa.
- B/79: po wylogowaniu stary token nie pozwala złożyć zamówienia.
- B/80: równoczesne poprawne i niepoprawne zamówienie nie powoduje sprzedaży ponad stan. W zależności od kolejności walidacji niepoprawne żądanie może otrzymać 409 lub 422.

## Wyniki i ograniczenia

Nowe testy: **5 zaliczonych** (`python -m pytest -q tests/test_transaction_safety_b76_b80.py`). Uruchomiono również pełną regresję, lecz nie ukończyła się przed limitem czasu środowiska; brak potwierdzenia pełnego zestawu. Testy korzystają z lokalnej bazy SQLite i TestClient. Nie wykonywano testów na PostgreSQL, Neon ani fizycznym telefonie. Nie podłączano prawdziwych płatności. Testy B/76–B/80 nie wprowadzają zmian do produkcyjnej logiki zamówień — dodają kontrole regresyjne.
