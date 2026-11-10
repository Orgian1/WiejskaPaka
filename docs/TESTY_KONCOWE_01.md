# Duży etap: testy końcowe i kontrola gotowości (część 1)

## Wykonane
- Dodano niezależny audyt kodu tras API (wykrywanie powielonych ścieżek i metod).
- Dodano testy własności rozliczeń dla każdej kwoty od 0 do 1000 groszy oraz dużych kwot.
- Dodano kontrolę podstawowych plików oraz jawne oznaczenie braku gotowości produkcyjnej.
- Uruchomiono pełen lokalny zestaw testów; wyniki poniżej.

## Niepotwierdzone i niewykonane
- Brak działającego serwera PostgreSQL w tym środowisku; test integracyjny nie został wykonany.
- Nie wykonano rzeczywistych testów mobilnych w przeglądarce ani audytu penetracyjnego.
- Brak integracji PSP, wypłat bankowych i weryfikacji prawnej. Nie należy uruchamiać sprzedaży.
- Strona publiczna i DNS nie były modyfikowane.

## Polecenia
`python -m backend.project_audit`
`python -m pytest -q tests`
