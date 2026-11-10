# WiejskaPaka — B/91–B/95: granice HTTP

Dodano pięć testów regresyjnych: (91) brak cache prywatnych odpowiedzi 401, (92) nagłówki bezpieczeństwa przy 422, (93) brak anonimowych zakupów, (94) nieudane logowanie nie tworzy sesji, (95) publiczny katalog nie ujawnia prywatnych pól użytkownika.

## Weryfikacja

`python -m pytest -q tests/test_b91_b95_http_boundaries.py` — 5 passed.

Pełną regresję uruchomiono, lecz nie ukończyła się przed limitem czasu wykonania. Nie jest oznaczona jako zaliczona. Testy działają na lokalnym SQLite; nie przeprowadzono testów na Neon/PostgreSQL ani na fizycznym telefonie.

## Otwarte kwestie

Zidentyfikować wolny/zawieszający się fragment pełnego zestawu testów; przeprowadzić testy na izolowanym PostgreSQL, ocenić RLS, sprawdzić działanie aplikacji na prawdziwym telefonie. Brak integracji produkcyjnych płatności.
