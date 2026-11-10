# WiejskaPaka B/56–B/60 — audyt integralności symulacji rozliczeń

Wprowadzono **tylko odczytowy** audyt tabel symulowanych płatności. Nie ma połączenia z operatorem płatności, bankiem ani Neon. Audyt nie naprawia danych automatycznie i nie udostępnia danych osobowych.

- B/56: weryfikacja pełnego zwrotu w groszach.
- B/57: wykrywanie jednoczesnego zwrotu i wypłaty oraz przekroczeń kwot.
- B/58: porównanie kwot symulacji z oryginalnym zamówieniem.
- B/59: sprawdzanie spójności statusu zamówienia i zwrotu/wypłaty.
- B/60: wykrywanie osieroconych zdarzeń oraz pięć testów regresyjnych.

Uruchomienie z katalogu projektu (wyłącznie istniejąca baza SQLite):

`python -m scripts.audit_test_payments --sqlite /sciezka/do/lokalnej/bazy.sqlite3`

Kod wyjścia 0 oznacza brak wykrytych niespójności; 1 oznacza wykryte problemy. Brak wykrytych problemów nie potwierdza gotowości produkcyjnej. Weryfikacja PostgreSQL/RLS, płatności i testy na telefonie pozostają otwarte.
