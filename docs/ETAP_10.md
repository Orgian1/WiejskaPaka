# Etap 10 backendu — powiadomienia w aplikacji

- Powiadomienia zapisywane w tej samej transakcji co zdarzenia zamówień (atomowość).
- Osobna skrzynka użytkownika, licznik nieprzeczytanych, oznaczanie jako przeczytane.
- Role klient/rolnik/przypisany dostawca; brak publicznych numerów telefonów.
- Powiadomienia nie zawierają PIN-u ani adresu dostawy.
- Zmiana statusu zamówienia jest nadal demonstracyjna; brak zewnętrznych wysyłek i płatności.
- PostgreSQL wymaga wykonania database/upgrade_09.sql oraz upgrade_10.sql przed uruchomieniem kodu.
- Nie przetestowano integracji z działającym PostgreSQL; testy korzystają z lokalnego SQLite.
