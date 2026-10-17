# Pakiet B/13 — historia zamówień w panelach

- Historia zamówienia jest wyświetlana w jednym miejscu karty, bez dublowania wpisów po ponownym kliknięciu.
- Odpowiedzi wcześniejszych żądań są ignorowane, jeśli w międzyczasie uruchomiono nowsze pobieranie historii.
- Po wylogowaniu lub usunięciu karty odpowiedź nie jest wyświetlana.
- Przy błędzie sieci użytkownik otrzymuje czytelny komunikat bez ujawniania szczegółów serwera.
- Dodano trzy testy regresyjne. Pełna lokalna seria: 2446 zaliczonych, 6 pominiętych, 16 podtestów zaliczonych.

Ograniczenia: nie wykonano testów na fizycznym telefonie ani na rzeczywistym PostgreSQL. Nie zmieniano Neon, wiejskapaka.pl ani płatności.
