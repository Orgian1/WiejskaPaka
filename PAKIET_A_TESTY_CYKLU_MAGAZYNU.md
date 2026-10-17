# Pakiet A — test cyklu magazynowego

Dodano `tests/test_inventory_lifecycle_package.py`: scenariusz trzech klientów, wyczerpania magazynu, odmowy sprzedaży ponad stan, anulowania, jednokrotnego przywrócenia towaru, ponownego zakupu i odmowy anulowania cudzego zamówienia. Sprawdzane są też kwoty w groszach.

## Wynik
Pełny zestaw testów uruchomiony po usunięciu starej lokalnej bazy SQLite: **2407 zaliczonych, 6 pominiętych, 16 podtestów zaliczonych**. Przy pierwszym uruchomieniu z istniejącą bazą było 20 błędów związanych z powtarzanymi danymi; po wyczyszczeniu środowiska testowego błędy nie wystąpiły. To wskazuje również na potrzebę dalszej izolacji testów.

## Ograniczenia
Nie przeprowadzono rzeczywistych testów PostgreSQL/Neon. RLS nie został włączony. Płatności są testowe. Strona publiczna nie była zmieniana.
