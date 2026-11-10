# WiejskaPaka — B/1201–B/1260: regresja i raportowanie

- Uruchomiono niezależnie 13 modułów testowych obejmujących koszyk, przesyłki, PIN, dostawców, anulowanie, zwroty i audyt finansowy: 13/13 PASS.
- Test modułu B/1141 uruchomiony osobno: 2 PASS; uruchomienie go w dużej sekwencji przekroczyło limit czasu środowiska, więc nie wliczamy go do 13 ukończonych modułów.
- Poprawiono raport testowy: `complete` oznacza, że wykonano wszystkie wybrane moduły, natomiast `success` oznacza, że wszystkie zakończyły się sukcesem. Raport zawiera także `planned`, `executed`, `passed`, `failed`.
- Dodano dwa testy sprawdzające raport zakończonego przebiegu z sukcesem i z porażką.
- Brak zmian produkcyjnej bazy danych, domeny i płatności.
- Pełna regresja wszystkich modułów oraz testy z PostgreSQL nadal oczekują na wykonanie.
