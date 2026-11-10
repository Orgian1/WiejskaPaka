# Pakiet B/07 — samodzielny scenariusz demonstracyjny

Uruchom z katalogu projektu: `python scripts/demo_journey.py`.

Skrypt sam tworzy **tymczasową SQLite**, usuwa zmienne połączenia PostgreSQL z procesu,
wykonuje transakcje **wyłącznie testowe** i usuwa bazę po zakończeniu.
Nie uruchamia serwera dostępnego z internetu i nie tworzy kont w Neon.

Scenariusz obejmuje: rejestrację rolnika, klienta i kuriera; produkt; punkt odbioru;
zamówienie odbioru i potwierdzenie jednorazowym PIN-em; zamówienie dostawy;
przypisanie kuriera; ukrycie adresu przed wysyłką i po doręczeniu; odmowę
potwierdzenia przez klienta; sprawdzenie kwot w groszach i końcowych statusów.

**To nie jest test w przeglądarce telefonu.** Do dalszych prac należą testy UI,
rzeczywistego odizolowanego PostgreSQL, RLS, hostingu i integracji płatności.
