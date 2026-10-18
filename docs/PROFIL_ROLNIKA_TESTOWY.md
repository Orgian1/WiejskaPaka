# Przypomnienie o profilu i potwierdzanie zasad demo

Panel rolnika zawiera sekcję „Zasady sprzedaży — demo”. Przycisk „Sprawdź stan
profilu” pobiera bieżący stan z API. Dane są pobierane na żądanie i usuwane przy
zmianie konta lub wylogowaniu. Potwierdzenie wymaga zaznaczenia zapoznania się
z wyświetlonymi zasadami. Powtórzenie żądania nie tworzy drugiego zdarzenia.

Po **20 zakończonych transakcjach** pojawia się przypomnienie o przeglądzie
profilu. To ustalona reguła produktu, nie interpretacja progów prawnych.

- Przesyłka obejmująca kilka produktów liczy się raz, gdy wszystkie jej
  pozycje mają status `odebrane` i należą do jej sprzedawcy oraz kupującego.
- Dawne zamówienie bez powiązania z przesyłką liczy się osobno po odbiorze.
- Przesyłki częściowo odebrane, anulowane, nieudane i oczekujące nie zwiększają
  licznika. Pusta grupa także nie jest transakcją.
- Licznik dotyczy zalogowanego rolnika. Jest obliczany z bieżących statusów;
  nie stanowi rejestru podatkowego, historii obrotu ani ewidencji prawnej.
- Potwierdzenie zasad oznacza stan `pending`; nie usuwa przypomnienia.
  Dopiero testowe zatwierdzenie przez administratora dla bieżącej wersji zasad
  wycisza je. Ponowna decyzja `needs_information` ponownie je pokazuje.

Odczyt: `GET /farmers/me/compliance`. Nowe pola:
`completed_transaction_count`, `profile_reminder_threshold`,
`profile_reminder_due`, `threshold_basis`, `current_rules_version`.
Istniejący `order_count_observed` pozostaje liczbą pozycji zamówień i nie
służy do przypomnienia. Potwierdzenie:
`POST /farmers/me/compliance/acknowledge` z `rules_version` i `accepted: true`.
Uprawnienia kontroluje serwer. Potwierdzenie nie umożliwia samodzielnego
zatwierdzenia przez rolnika i nie uruchamia wypłat.

Nie dodano pól PESEL, NIP, daty urodzenia ani rachunku bankowego. Demo nie
zbiera danych tożsamości. Właściwa weryfikacja i wypłaty pozostają osobnym
procesem produkcyjnym. Nie wprowadzono blokady zakupów lub sprzedaży po
przekroczeniu progu: przypomnienie służy odbiorowi wersji testowej.

Testy: granice 0/19/20/21, zamówienia dawne i wieloproduktowe, stan częściowy,
zwroty/anulowania, odseparowanie sprzedawców, testowe decyzje, zgoda i role HTTP,
podwójne kliknięcia, błędy sieci oraz odpowiedź po zmianie konta. Testy Chromium
na 320 i 1280 px wymagają faktycznej przeglądarki; bez niej mają status SKIP.
