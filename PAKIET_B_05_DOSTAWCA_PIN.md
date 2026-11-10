# Pakiet B/05 — potwierdzanie doręczenia przez dostawcę

- Panel dostawcy odróżnia pozytywne potwierdzenie PIN-em od nieprawidłowego PIN-u. Wcześniej zawsze wyświetlał ogólny komunikat o zapisaniu wyniku, niezależnie od odpowiedzi.
- Po błędnym PIN-ie wyświetla pozostałą liczbę prób, bez odświeżania całego panelu.
- Podczas wysyłania potwierdzenia przycisk jest zablokowany; PIN zostaje wyczyszczony także po błędzie żądania.
- Po zmianie sesji opóźniona odpowiedź nie aktualizuje komunikatu panelu.
- Dwa testy regresyjne; pełna lokalna seria: 2425 zaliczonych, 6 pominiętych, 16 podtestów zaliczonych.

## Ograniczenia
Testy statyczne kodu i lokalny zestaw pytest nie zastępują ręcznych testów przeglądarki mobilnej ani testów rzeczywistego PostgreSQL. Nie zmieniono Neon, strony publicznej ani rzeczywistych płatności.
