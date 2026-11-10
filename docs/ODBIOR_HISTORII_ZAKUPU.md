# Odbiór funkcji historii zakupu w innym środowisku

Ta lista opisuje pracę pozostającą do wykonania na działającym PostgreSQL
i Chromium. Nie jest protokołem zaliczonych testów tej sesji.

## Lokalny PostgreSQL

1. Użyć `docker-compose.postgres.yml` i instrukcji `POSTGRESQL_TESTY_LOKALNE.md`.
   Testy muszą dotyczyć jednorazowej bazy lokalnej; nie podłączać Neon ani
   rzeczywistych danych użytkowników. Nie uruchamiać GitHub Actions.
2. Uruchomić natywną bramę API z `tests/test_postgres_full_api_optin.py`,
   w tym `test_native_purchase_record_is_private_and_insert_only`.
   Sam parser SQL lub zgodność adaptera SQLite nie zalicza tego kroku.
3. Potwierdzić instalację wszystkich migracji, w tym
   `upgrade_b10921_purchase_records.sql`, przez rolę migracyjną. Aplikacja
   działa jako odrębna rola bez uprawnień właściciela i administratora.
4. Sprawdzić brak prawa do usunięcia triggera/tabeli i TRUNCATE przez rolę
   aplikacji; uruchomić próby UPDATE/DELETE rekordu i naruszenia kwot.
5. Powtórzyć wyścigi checkout/edycja produktu, checkout/edycja punktu,
   odczyt/zwrot i odczyt/cofnięcie sesji na rzeczywistych transakcjach PostgreSQL.
   Dopiero wynik z tej bazy potwierdza jej blokady i autoryzację.

## Rzeczywista przeglądarka

Używać wyłącznie danych syntetycznych i płatności testowych. Uruchomić serwer
według README, sprawdzić mały ekran oraz pulpit.

1. Utworzyć konta rolnika i klienta, dwa produkty oraz punkt z adresem/godzinami.
2. Kupić odbiór w punkcie. Na karcie zamówienia pokazać pierwotne warunki
   i pobrać JSON. Sprawdzić nazwę, cenę, daty, punkt i zero opłaty za dostawę.
3. Zrealizować odbiór PIN-em. Zmienić ofertę i adres/godziny punktu. Odczyt
   oraz nowy eksport mają nadal zawierać dane z chwili zakupu.
4. Kupić dostawę dwóch produktów jako jedną przesyłkę. W podglądzie całej
   przesyłki ma być jedna opłata. Symulować płatność i winę dostawcy:
   suma zwrotów obejmuje całą zapłaconą kwotę, a oryginał się nie zmienia.
5. Sprawdzić JSON: bez PIN-u, telefonu, adresu dostawy klienta, hasła i tokenu.
   W pobranym pliku znajdują się warunki zakupu; użytkownik powinien chronić
   go tak jak inne dokumenty dotyczące swoich zakupów.
6. Sprawdzić brak dostępu z obcego konta i konta dostawcy. Administrator
   otrzymuje audyt zgodności, bez podglądu prywatnych warunków przez te endpointy.
7. Ograniczyć sieć w narzędziach przeglądarki, opóźnić odpowiedź i wylogować
   konto albo zmienić kartę. Nie może nastąpić render ani pobranie starego zapisu.
8. Odwrócić kolejność odpowiedzi dwóch żądań. Starsza odpowiedź nie może
   zastąpić nowszego podglądu, także w szczegółach i historii finansowej przesyłki.
9. Sprawdzić zamówienie sprzed migracji: komunikat o braku zapisu, bez
   podstawiania obecnej oferty. Zapis testowy nie może być opisany jako faktura
   lub potwierdzenie prawdziwej zapłaty.
10. Sprawdzić klawiaturę, czytelność, pobieranie i otwieranie JSON oraz
    polskie znaki w nazwach. Zanotować wersję przeglądarki i rzeczywisty wynik.

Po tych pracach zapisać oddzielny raport z liczbą PASS/FAIL/SKIP, wersją kodu
i bazą. Nie zmieniać historycznych raportów z tej sesji na PASS.
