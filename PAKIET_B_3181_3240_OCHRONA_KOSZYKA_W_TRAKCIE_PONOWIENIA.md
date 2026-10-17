# WiejskaPaka B/3181–B/3240 — ochrona koszyka przy niepewnym wyniku zakupu

## Zmiana
Jeżeli żądanie zakupu zostało wysłane, ale wynik pozostaje nieznany (np. zerwane połączenie), interfejs zachowuje klucz idempotencji oraz blokuje dodawanie, usuwanie i zmianę ilości produktów w koszyku. Klient może ponowić zakup z tym samym identyfikatorem i parametrami. Po potwierdzonej odpowiedzi zabezpieczenie jest zwalniane. Zmiana konta czyści stan zgodnie z dotychczasową polityką sesji.

## Dlaczego
Bez tej ochrony klient mógł zmodyfikować koszyk i ponowić zakup, a serwer zwróciłby wynik poprzedniej operacji. Blokada ogranicza niejasności między stanem koszyka a wcześniej wysłanym zakupem.

## Ograniczenia
Identyfikator jest przechowywany tylko w pamięci strony; po jej odświeżeniu należy sprawdzić historię zamówień. Testy kontraktowe sprawdzają obecność zabezpieczeń w kodzie, nie zastępują testu na fizycznym telefonie. Płatności pozostają wyłącznie testowe. Nie zmieniano konfiguracji Neon.
