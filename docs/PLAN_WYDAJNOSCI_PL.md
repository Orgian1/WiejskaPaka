# Plan wydajności polskiej WiejskaPaki

Jedyna obecna aplikacja obsługuje Polskę, język polski i PLN. Nie wdrażamy zagranicznych walut ani języków.

## Cele

- Pilotaż lokalny: 20 sprzedawców i 1000 kupujących dziennie.
- Pierwszy cel: 50 sprzedawców i 5000 kupujących dziennie.
- Są to cele projektowe, a nie potwierdzona wydajność.

## Jawny model ruchu

Zakładając 20 żądań na kupującego i 20% ruchu w godzinie szczytu, szacujemy 100000 żądań dziennie, 20000 w godzinie szczytu i około 6 żądań/s średnio w szczytowej godzinie. Krótkie skoki mogą być znacznie wyższe. Założenia są zapisane w backend/capacity_targets.py.

## Warunki odbioru

1. Pełna regresja Windows, PostgreSQL i Chromium na tym samym commicie.
2. Testy HTTP z PostgreSQL oraz realistycznymi danymi 50 sprzedawców.
3. Pomiary p50/p95/p99, błędów 5xx, CPU, RAM, blokad i połączeń z bazą.
4. Test równoczesnego zakupu ostatniej sztuki, powtórzeń żądań i awarii bazy.
5. Kopie zapasowe, próba odtworzenia, monitoring i limity ruchu.
6. Audyt bezpieczeństwa i prawny przed zdjęciem blokady produkcyjnej.

Benchmark SQLite nie potwierdza wydajności HTTP/PostgreSQL. Domena jest kupiona, ale serwer, prawdziwe e-maile i płatności nie są podłączone.
