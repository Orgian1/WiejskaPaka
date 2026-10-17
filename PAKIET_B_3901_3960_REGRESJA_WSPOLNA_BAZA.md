# WiejskaPaka B/3901–B/3960 — regresja wspólnej bazy

- Próba pełnej regresji (`python scripts/run_tests_isolated.py -q`) wykazała wiele niepowodzeń przed przerwaniem; nie została ukończona i nie jest zaliczona.
- Ponowienie w trybie `-x` zatrzymało się na pierwszym błędzie: test B/1321 liczył wszystkie produkty w bazie zamiast produktów utworzonych przez ten test (73 testy zaliczone, 1 niezaliczony).
- Poprawiono selekcję produktów w teście B/1321 oraz produktów, przesyłek, zamówień i kluczy idempotencji w B/1681, aby weryfikować tylko własne dane testowe.
- Testy obu poprawionych modułów na izolowanej bazie: 2 passed.
- Testy B/3541, B/3481, B/3781: 5 passed.
- Nie potwierdzono pełnej regresji ani PostgreSQL, przeglądarki czy urządzeń fizycznych.
- Nie zmieniano Neon ani nie podłączano prawdziwych płatności.
