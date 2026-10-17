# WiejskaPaka — B/6601–B/6960: inwentaryzacja API i testy akceptacyjne

## Zweryfikowane w tej paczce
- Automatycznie zinwentaryzowano 87 metod/ścieżek API, w tym 72 oznaczone jako priorytetowe do ręcznego przeglądu autoryzacji.
- Dodano `scripts/audit_endpoint_inventory.py` i 3 nowe testy: 3/3 PASS.
- Ponownie wykonano cztery zestawy akceptacyjne HTTP: 4/4 PASS (szczegóły w `RAPORT_HTTP_AKCEPTACJA_B_6601_6960.json`).
- Składnia JS i kompilacja Python: PASS.
- Test Chromium z lokalnym HTTP: BLOCKED przez politykę środowiska (niezaliczony).
- Brak dostępnego lokalnego serwera PostgreSQL: rzeczywista integracja nadal niewykonana.

## Ważne ograniczenia
Inwentaryzacja jest listą tras do ręcznej kontroli, a nie potwierdzeniem bezpieczeństwa 72 tras. Nie zmieniano konfiguracji Neon ani nie podłączano płatności produkcyjnych, hostingu czy domeny. Testy HTTP korzystają z izolowanej bazy SQLite.

## Kolejne działania
1. Ręczna weryfikacja autoryzacji 72 tras wysokiego priorytetu, z dowodami testów odmowy dostępu.
2. Integracja na odizolowanym PostgreSQL.
3. Testy Chromium po HTTP w środowisku bez blokady localhost.
4. Fizyczne telefony, audyt prawny i gotowość produkcyjna.
