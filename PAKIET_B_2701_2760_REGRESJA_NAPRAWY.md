# WiejskaPaka B/2701–B/2760 — regresja i naprawy

Uruchomiono cztery części regresji z poprzednich raportów (73 zaliczone moduły) i kontynuowano je. W aktualnych raportach jest 115/200 wykonanych pozycji, z czego 112 miało wynik pozytywny, a trzy ujawniły niezgodności testów z aktualnym interfejsem i cyklem życia zamówienia.

Poprawki:
- test mobilny oczekuje pięciu, a nie czterech odnośników w nawigacji;
- usunięto ze zwykłego komentarza w dashboard.js słowa, które test błędnie interpretował jako użycie niebezpiecznego API HTML lub pamięci lokalnej;
- przykładowy rekord w teście audytu używa poprawnego statusu `oczekuje_na_platnosc_testowa`, a nie przestarzałego `nowe`.

Ponowne uruchomienie trzech dotkniętych plików: 11 testów zaliczonych. Kompilacja backendu i skryptów: OK.

Uwaga: trzy zmienione moduły mają nowe sumy SHA-256. Raporty częściowe odzwierciedlają stan przed poprawkami i nie są pełnym aktualnym potwierdzeniem regresji. Pozostałe 85 modułów nie zostało uruchomionych w tym pakiecie. Nie przeprowadzono testów PostgreSQL ani kompleksowych testów przeglądarkowych. Nie podłączono produkcyjnych usług.
