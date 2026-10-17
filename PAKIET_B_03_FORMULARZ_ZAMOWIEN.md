# Pakiet B/03 — bezpieczeństwo formularza zamówienia

- Zablokowano wielokrotne kliknięcie „Zamów testowo” podczas trwającego żądania. Przycisk zostaje odblokowany w `finally` także po błędzie.
- Dodano kontrolę całkowitej dodatniej liczby sztuk i aktualnie wyświetlanego stanu magazynu przed wysłaniem żądania. Ostateczna walidacja i ochrona magazynu pozostają po stronie serwera.
- Dodano weryfikację niepustego miasta i ulicy oraz polskiego kodu pocztowego przy dostawie.
- Zabezpieczono listę punktów odbioru przed nadpisaniem przez spóźnioną odpowiedź, kiedy klient zmienił tryb na dostawę.
- Dodano trzy testy regresyjne. Wynik całej lokalnej serii: 2420 zaliczonych, 6 pominiętych, 16 podtestów zaliczonych.

Ograniczenia: testy frontendu w tym pakiecie sprawdzają obecność zabezpieczeń w kodzie, a nie zachowanie na prawdziwym telefonie. Brak rzeczywistych płatności i testów serwera PostgreSQL. Neon i publiczna strona pozostają bez zmian.
