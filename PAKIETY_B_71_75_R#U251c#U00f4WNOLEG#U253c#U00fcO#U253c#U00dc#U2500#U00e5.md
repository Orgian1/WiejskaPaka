# Pakiety B/71–B/75 — równoległe operacje i izolacja kont

Dodano `tests/test_parallel_access_b71_b75.py` z pięcioma testami na prawdziwych endpointach FastAPI i izolowanej bazie SQLite:

- B/71: dwóch klientów walczy o ostatnią sztukę; dokładnie jedno zamówienie jest przyjęte.
- B/72: przy dwóch sztukach oba równoległe zakupy mogą się udać.
- B/73: cztery równoległe żądania jednego klienta nie sprzedają jednej sztuki czterokrotnie.
- B/74: rolnik i dostawca nie mogą składać zamówień jako klient.
- B/75: obcy klient nie widzi adresu, zdarzeń ani zamówienia innej osoby.

Testy docelowe: **5 zaliczonych**. Próba pełnego zestawu dotarła do 93%, lecz nie zakończyła się przed limitem czasu środowiska. Nie należy przedstawiać całego zestawu jako zaliczonego. Testy dotyczą SQLite i nie dowodzą poprawności równoległych transakcji w PostgreSQL. Nie wykonano operacji na Neon ani na stronie produkcyjnej.
