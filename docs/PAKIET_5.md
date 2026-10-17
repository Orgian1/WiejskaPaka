# Pakiet 5/5 — finalizacja wersji developerskiej

## Zmiany
- Ulepszono responsywność i nawigację klawiaturą (link do treści, widoczny fokus, zmniejszone animacje, dotykowe przyciski).
- Dodano `python -m backend.release_audit` — audyt plików, zgodności tabel i flag developerskich; pokazuje **niezaliczone ręczne wymagania** i zawsze wskazuje brak gotowości produkcyjnej.
- Dodano test przepływu zamówienia: rolnik → produkt → klient → dostawa → dostawca → kontrola towaru → PIN → historia; oraz testy audytu i struktury interfejsu.

## Ograniczenia przed wdrożeniem
Nie wykonano testów interfejsu na urządzeniach, testów na żywym PostgreSQL, testów wydajnościowych, pełnego audytu RODO i bezpieczeństwa ani integracji z operatorem płatności. Wymagane są również przegląd prawny regulaminów, DAC7, procedury KYC, backup i odzyskiwanie danych, obserwowalność i testy awaryjne. Testy automatyczne nie potwierdzają zgodności z prawem.

Publiczna strona wiejskapaka.pl bez zmian. Nie uruchamiać płatności produkcyjnych. Pięć pakietów stanowi plan prac developerskich, a nie deklarację gotowości do komercyjnego uruchomienia.
