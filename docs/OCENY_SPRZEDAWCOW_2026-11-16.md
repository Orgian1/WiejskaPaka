# Oceny sprzedawców po odbiorze zakupu

Funkcja bazuje na PR #63 (wraz ze zmianami #62). Kupujący może w historii zamówień wybrać 1–5 gwiazdek i nacisnąć „Zapisz ocenę”. Ocena jest dostępna wyłącznie dla jego zamówienia o statusie `odebrane`, z wykorzystanym PIN-em i zapisanym potwierdzeniem odbioru. Zasady odbioru, PIN-u, płatności, prowizji, zwrotów i portfela pozostają bez zmian.

Jeden rekord oceny przypada na jedno zamówienie. Oceny nie można zmienić ani usunąć przez API. Ponowienie tego samego zapisu zwraca poprzednią ocenę bez zwiększenia licznika; próba zmiany gwiazdek zwraca 409. Przy kilku pozycjach przesyłki ocenia się osobno zamówienia widoczne w historii, nie każdą sztukę produktu. Nie wprowadzono ocen kupujących przez sprzedawców ani komentarzy tekstowych.

Średnia i licznik ocen są widoczne przy ofertach, w wyszukiwarce sprzedawców, przy odebranym zakupie i w panelu sprzedawcy. Brak ocen jest oznaczony jako „brak ocen (0)”, a nie zero gwiazdek. Zapis odświeża widoczne liczniki. Odświeżenie listy pobiera nowe dane, a wylogowanie usuwa prywatne kontrolki i pamięć ocen. Interfejs jest dostępny klawiaturą, ma etykiety przycisków i działa w widokach 320 oraz 1280 px.

## API i bezpieczeństwo

| Trasa | Dostęp | Wynik |
| --- | --- | --- |
| GET `/farmers/{farmer_id}/ratings` | publiczny | wyłącznie ID sprzedawcy, średnia i licznik |
| GET `/orders/{order_id}/seller-rating` | właściciel zakupu, klient | własna ocena lub null oraz ID sprzedawcy |
| POST `/orders/{order_id}/seller-rating` | właściciel odebranego zakupu, klient | `{stars:1..5}`; zapis jednokrotny |

Tożsamość pochodzi z ważnej sesji, nigdy z pola buyer_id, farmer_id czy actor_id klienta. Zapis ponownie uwierzytelnia użytkownika w tej samej transakcji i blokuje zamówienie (`FOR UPDATE` na PostgreSQL, `BEGIN IMMEDIATE` na SQLite). Klucz główny order_id blokuje duplikaty. Dane dotyczące zamówienia i sprzedawcy są wyprowadzane z bazy. Wartości poza 1–5, boolean, ułamki, tekst i dodatkowe parametry są odrzucane. Brak endpointów UPDATE/DELETE; PostgreSQL odbiera te prawa wykonawcy, a SQLite ma blokujące triggery.

RLS chroni pojedyncze rekordy przed odczytem przez innych kupujących, sprzedawcę i kuriera. Administrator ma dotychczasowy dostęp diagnostyczny; zwykłe API nie zwraca listy autorów ocen. Publiczne statystyki oblicza wąska funkcja `wp_rls.seller_rating_summary(bigint)` należąca do roli guard, z ustalonym search_path. Zwraca wyłącznie COUNT/SUM; nie przyjmuje SQL ani tożsamości. Backend wylicza średnią z tej pary. Dane kupującego, PIN, tokeny, adresy i identyfikatory poszczególnych ocen nie są publikowane. Dostęp do funkcji odbywa się przez podpisany gateway, bez bezpośrednich uprawnień fizycznego konta aplikacji. Polityki weryfikują zgodność order_id/buyer_id/farmer_id i potwierdzony odbiór także dla podpisanych zapytań. Same GUC nie nadają tożsamości. Polityki odnoszą się do właściwej tabeli ocen: wyjątki bootstrapu logowania nie dają kontekstowi auth bez użytkownika prawa odczytu ani tworzenia ocen.

## Migracje i wdrożenie

Migracje są przygotowane do ręcznego przeglądu; niczego nie wdrożono na VPS ani na produkcyjnej bazie. PostgreSQL nie migruje automatycznie podczas uruchamiania aplikacji.

1. Uruchomić testy funkcji oraz pełną bramkę RLS na jednorazowym lokalnym PostgreSQL. Następnie zweryfikować rzeczywiste ACL, właścicieli, klucz gateway, backup i odtworzenie na kopii docelowej bazy. Dotychczasowe ograniczenia produkcyjne PR #62/#63 pozostają.
2. Zatrzymać API/workery, wykonać kopię i zastosować `database/security_rls/003_seller_ratings.up.sql` osobnym kontem migracyjnym. Ustawienie sesji `wp_rls.api_compatibility_verified='yes'` wolno zadeklarować wyłącznie po sprawdzeniu zgodności API; sama flaga nie jest dowodem testów. Wyjątek testowy wymaga jednocześnie bazy `wp_test_*` i `wp_rls.disposable_test='yes'`.
3. Sprawdzić ENABLE/FORCE RLS, pięć polityk, brak bezpośrednich ACL i własności tabeli po stronie konta aplikacji, brak SUPERUSER/BYPASSRLS oraz brak publicznego EXECUTE funkcji agregującej. Wykonać próby cudzych odczytów, zapisów przed odbiorem i ponownego głosowania. Nie przyznawać aplikacji roli migracyjnej.
4. Dla nowej bazy testowej manifest zawiera `optional_seller_ratings.sql`, potem provision stosuje 001, 002 i 003. Nie stosować samej deklaracji tabeli na działającej bazie już chronionej RLS.
5. Uruchomić kod i sprawdzić klienta, sprzedawcę, publiczną średnią oraz portfel. W tej pracy nie wykonano żadnego z tych kroków na produkcji ani rzeczywistych płatności PayU.

Preferowany rollback zachowuje oceny: przywrócić poprzedni kod i pozostawić nową tabelę do przeglądu. Pełne wycofanie schematu: zatrzymać API/workery, zarchiwizować oceny, wycofać kod funkcji i zastosować `003_seller_ratings.down.sql`. Skrypt usuwa wyłącznie tabelę ocen, jej funkcję agregującą i wpis metadanych; **usuwa dane ocen**. Nie cofać 001/002 ani nie poszerzać uprawnień aplikacji. Nieznane polityki blokują migrację i rollback do ręcznego przeglądu. Test down/up porównuje niezmienione zamówienia i rekordy finansowe.

## Weryfikacja

```sh
python -m pytest -q tests/test_seller_ratings_http.py tests/test_seller_ratings_browser.py tests/test_seller_ratings_rls.py
python -m scripts.run_rls_api_gate --select seller_ratings
python -m scripts.run_rls_api_gate
python scripts/run_full_regression.py --shard 1/2 --timeout 360 --report work/seller-ratings-full-1.json
python scripts/run_full_regression.py --shard 2/2 --timeout 360 --report work/seller-ratings-full-2.json
```

Wyniki końcowe zostaną dołączone do raportu i PR. Testy obejmują rzeczywisty odbiór PIN-em, nieodebrane/anulowane/cudze zakupy, dwie równoczesne oceny, idempotencję, licznik z wielu kont, prywatność, wylogowanie, trwałość, spoofing GUC, niedozwolone SQL, migrację i rollback oraz Chromium na telefonie/komputerze. Telefon oznacza responsywny Chromium, nie fizyczny iOS/Safari. Nie ma moderacji, edycji ani komentarzy tekstowych; zakres obejmuje jednokrotne gwiazdki za odebrany zakup.
