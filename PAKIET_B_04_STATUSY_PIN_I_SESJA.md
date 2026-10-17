# Pakiet B/04 — statusy, PIN i prywatność panelu

- Panel dostawcy pozwala na potwierdzenie PIN-em tylko dla zamówienia o statusie `w_drodze_testowo` (nie oferuje przycisku na innych etapach).
- Panel rolnika waliduje 6 cyfr i potwierdzenie sprawdzenia produktów przed wysłaniem żądania; blokuje przycisk na czas żądania i czyści PIN po odpowiedzi.
- Panel i powiadomienia kontrolują generację sesji po operacjach asynchronicznych, żeby odpowiedzi rozpoczęte przed wylogowaniem nie przywróciły prywatnych widoków. Historia statusów sprawdza też, czy karta jest nadal podłączona do DOM.
- 3 nowe testy regresyjne oraz sprawdzenie składni JavaScript.
- Pełne testy lokalne: 2423 zaliczone, 6 pominiętych, 16 podtestów zaliczonych (świeża SQLite).

Ograniczenia: testy JavaScript są testami strukturalnymi, nie zastępują testów E2E w przeglądarce. PostgreSQL/Neon nie został połączony ani zmodyfikowany. Brak prawdziwych płatności. Nie zmieniano publicznej strony.
