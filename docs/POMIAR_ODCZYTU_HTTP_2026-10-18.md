# Lokalny pomiar odczytu HTTP — 18.10.2026

Wynik dodatkowej próby akceptacyjnej: **360 poprawnych odpowiedzi, zero 5xx,
zero błędów transportu i zero nieprawidłowych wyników**.
Raport: `audits/catalog_read_acceptance_2026-10-18.json`.

## Warunki

- Rzeczywisty serwer HTTP na 127.0.0.1 i jednorazowa SQLite.
- 50 syntetycznych sprzedawców, 5000 rekordów kupujących, 1000 ofert
  oraz 50 punktów o syntetycznych współrzędnych.
- Dane zasiane bezpośrednio w prywatnej bazie fixture; wspólny skrót hasła
  celowo upraszcza przygotowanie. Nie mierzono rejestracji i logowania.
- Zaplanowano 6 żądań/s przez około minutę: 180 wyszukiwań katalogu i
  180 wyszukiwań w okolicy. Limit puli to cztery zadania, nie deklaracja
  czterech stale jednoczesnych klientów.
- Czas 59,842 s, obserwowana średnia 6,016 żądania/s. Nie używano zewnętrznej
  bazy, prawdziwych kont, poczty ani płatności.
- Sprawdzano odpowiedź 200, rozmiar strony 24, całkowite grosze i właściwe
  wyniki: 334 dopasowania katalogu oraz dostępną dalszą stronę w okolicy.

## Zaobserwowane czasy

Percentyle obliczono metodą nearest-rank z czasu pełnego żądania HTTP.
Wartości opisują tę maszynę i ten zestaw danych, bez ustalonego SLA.

| Odczyt | Żądania | p50 | p95 | p99 | Maksimum |
| --- | --- | --- | --- | --- | --- |
| Paginowany katalog | 180 | 5,077 ms | 13,463 ms | 33,984 ms | 131,393 ms |
| Wyszukiwanie w okolicy | 180 | 6,738 ms | 16,698 ms | 26,688 ms | 39,660 ms |

5000 rekordów w bazie nie oznacza 5000 aktywnych ani równoczesnych klientów.
Ten przebieg nie testuje transakcji zakupu, sporów, haszowania haseł,
PostgreSQL, hostingu, transferu sieciowego poza loopback ani pracy całodobowej.
Nie potwierdza produkcyjnej obsługi 5000 kupujących dziennie. Nie dodaje
360 nowych przypadków pytest — to powtarzane żądania w jednym scenariuszu.

Założenie 6 żądań/s pochodzi z jawnego planu 5000 kupujących dziennie,
20 żądań na osobę i 20% ruchu w godzinie szczytu. Rzeczywisty ruch może mieć
inny profil, więcej odczytów punktów odbioru i gwałtowne skoki. Model i dalsze
warunki pomiaru PostgreSQL pozostają w `PLAN_WYDAJNOSCI_PL.md`.

Odciski kodu oraz testów w raporcie wiążą wynik z pakietem paginacji katalogu.
Po zakończeniu próby prywatna baza, klucz i syntetyczne konta zostały usunięte
wraz z katalogiem tymczasowym. Opublikowano wyłącznie oczyszczone metryki.
