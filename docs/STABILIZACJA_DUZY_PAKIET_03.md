# Stabilizacja — duży pakiet 03

## Poprawka prywatności
Po potwierdzeniu dostawy PIN-em dostęp dostawcy do adresu klienta zostaje automatycznie cofnięty (HTTP 403). Klient i rolnik nadal mają dostęp do danych własnego zamówienia zgodnie z dotychczasową polityką.

## Testy
Nowy test regresyjny sprawdza dostęp przed wysyłką, w trasie i po odbiorze.

## Ograniczenia
Nie przeprowadzono testów na działającym PostgreSQL, testów w przeglądarce ani niezależnego audytu. Dostęp rolnika do danych i retencja adresów wymagają osobnej polityki. Produkcyjne płatności pozostają wyłączone.
