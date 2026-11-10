# Etap backend 09 — dostawy i historia statusów

- Przypisanie istniejącego konta dostawcy przez rolnika do własnego zamówienia z dostawą.
- Wydanie dostawy w trybie testowym, potwierdzenie PIN-em przez przypisanego dostawcę.
- Historia zdarzeń zamówienia, widoczna tylko dla klienta, rolnika i przypisanego dostawcy.
- Migracja SQLite uruchamia się przy starcie; PostgreSQL wymaga ręcznego `database/upgrade_09.sql` przed startem aplikacji.
- Brak ujawniania numerów telefonów; endpointy nie zwracają adresu klienta dostawcy (do rozbudowy z kontrolą dostępu).
- UWAGA: system nadal nie posiada prawdziwego potwierdzania płatności, dlatego wszystkie zmiany statusu dostaw są wyłącznie testowe.
- Do dalszej pracy: rezerwacje i terminy dostaw, zdarzenia utworzenia zamówienia, integracja PostgreSQL, powiadomienia, reklamacje ustawowe, polityka zwrotów i faktury.
