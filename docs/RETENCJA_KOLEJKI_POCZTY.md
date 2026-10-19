# Jawna retencja metadanych kolejki — etap testowy

`reset_mail_queue.purge_terminal` usuwa ograniczoną partię metadanych
zakończonych zadań. Nie uruchamia się przy imporcie, starcie API,
uruchomieniu pracownika ani odtwarzaniu kopii. Wywołujący musi jawnie
otworzyć transakcję i zdecydować o jej zatwierdzeniu.

Do usunięcia kwalifikują się tylko stany accepted, uncertain, failed i
expired, których zaszyfrowany ładunek jest już usunięty, a od daty wygaśnięcia
zadania upłynął cały okres retencji. Domyślnie jest to 30 dni, z dopuszczonym
zakresem 1–365 dni. To ustawienie techniczne dla testów, nie określenie
prawnego okresu przechowywania danych ani gotowa polityka produkcyjna.

Partia ma domyślnie 100 wpisów, maksymalnie 1000. Kolejność wyznacza data
wygaśnięcia i identyfikator. Limit ogranicza liczbę usunięć, nie koszt
skanowania lub sortowania tabeli — pomiar i indeks dla dużych wolumenów
pozostają do odbioru wydajnościowego. Wynik zawiera tylko liczbę usuniętych
wpisów; nie zwraca odbiorców ani identyfikatorów zadań.

Zadania queued i leased pozostają nietknięte nawet po wygaśnięciu. Retencja
nie odzyskuje dzierżaw ani nie rozpoczyna transportu. Nie usuwa użytkowników,
sesji, tokenów resetu, limitów żądań ani danych zakupów. Usunięcie metadanych
nie może wznowić wysyłki — aktywne stany nie są kasowane przez tę funkcję.

SQLite wymaga transakcji zapisu BEGIN IMMEDIATE. PostgreSQL blokuje wybraną
partię przez FOR UPDATE SKIP LOCKED: pomija zajęte wpisy i pozwala kolejnym
wywołaniom odebrać je po zwolnieniu blokad. Błąd w transakcji wycofuje również
usunięcia. Nie ma automatycznych migracji ani nowych wymagań schematu.

Testy obejmują wszystkie stany końcowe, dokładną granicę wieku, zachowanie
queued/leased i tokenów, ograniczenie i powtórzenie partii, nowsze wpisy,
rollback i równoległe porządkowanie. Osobny test natywny PostgreSQL sprawdza
pominięcie zablokowanego wpisu i zachowanie aktywnego zaszyfrowanego zadania.
