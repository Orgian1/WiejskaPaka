# WiejskaPaka B/2881–B/2940 — pełna regresja i poprawki

Wykonano wszystkie cztery grupy po 50 modułów. W raporcie początkowym: 195 zaliczonych, 5 niezaliczonych. Zidentyfikowano nieaktualne asercje testów po zmianach interfejsu oraz problem w teście wylogowania.

Poprawiono ochronę przycisku potwierdzenia przesyłki w panelu dostawcy: blokada na czas żądania i zwolnienie w finally, czyszczenie PIN-u. Dostosowano cztery pliki testów do aktualnej obsługi przesyłek i resetowania koszyka podczas zmiany konta; 11 testów zaliczonych. Test wyścigu logowania pozostaje niezaliczony i wymaga osobnej diagnostyki (test Node uruchamiany z makietą DOM).

Raporty full_regression_shard_*.json zawierają wyniki sprzed ostatnich zmian, nie są już aktualnym potwierdzeniem pełnej regresji. Nie wykonano testów na PostgreSQL ani w prawdziwej przeglądarce. Neon i płatności produkcyjne bez zmian.
