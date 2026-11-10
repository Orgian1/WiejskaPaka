# WiejskaPaka — pakiet roboczy B/261–B/300

## Zaimplementowano
- Jednolita polityka dozwolonych zmian statusu zamówienia dla odbioru i dostawy.
- Blokowanie przeskakiwania etapów i przejść ze stanów końcowych.
- Włączenie kontroli do pięciu istniejących ścieżek API: potwierdzenie PIN, gotowość odbioru, anulowanie testowe, wysyłka testowa, nieudana dostawa testowa.
- 21 nowych przypadków testowych.

## Weryfikacja
- Testy modułu: 21 zaliczonych.
- Testy modułu i dwóch wcześniejszych zestawów zamówień: 29 zaliczonych.
- Kompilacja składni backendu: pomyślna.

## Granice
To nie jest 40 oddzielnych funkcji. Brak testów produkcyjnych Neon, brak rzeczywistych płatności, brak pełnej regresji. Polityka przejść jest kontrolą na poziomie aplikacji, nie zastępuje transakcji, uprawnień i blokad w bazie.
