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

## Kolejka administratora

Sekcja „Przegląd profili rolników — TEST” pokazuje profile po potwierdzeniu
zasad. Administrator pobiera listę na żądanie, filtruje stan i przegląda strony
po 20 pozycji. Lista zawiera identyfikator rolnika, wersję i datę potwierdzenia
zasad oraz stan i datę przeglądu. Nie zawiera e-maila, danych tożsamości,
rachunku, uzasadnień wcześniejszych decyzji ani danych zamówień.

Administrator wybiera zatwierdzenie testowe, prośbę o wyjaśnienie lub odrzucenie
i wpisuje fikcyjne uzasadnienie (3–500 znaków). Po zapisie odświeża kolejkę.
Zmiana konta usuwa wyniki i robocze uzasadnienie, również z odłączonych pól.
Po utracie odpowiedzi należy odświeżyć stan — decyzja mogła zostać zapisana.

`GET /admin/farmers/compliance-queue` przyjmuje opcjonalny `status`,
`limit` 1–50 i `offset` 0–10000. Domyślnie zwraca do 20 profili wszystkich
stanów; panel domyślnie filtruje oczekujące. Wynik ma stabilną kolejność ID,
`total` i `has_more`. Odczyt wymaga roli administratora.

Formularz do istniejącego żądania decyzji dołącza `expected_rules_version`,
`expected_review_status` i `expected_reviewed_at` (także jawne `null`).
Aktualizacja warunkowa porównuje cały ten stan. Jeśli inna decyzja zmieniła
profil, serwer zwraca 409 i nie zapisuje następnego zdarzenia. Data chroni
również przed powrotem statusu do poprzedniej wartości. Starsi klienci API,
którzy nie wysyłają żadnego pola `expected_*`, zachowują dotychczasowe działanie;
pełna ochrona starego widoku dotyczy nowego formularza i klientów wysyłających
kompletny stan. Niepełny zestaw pól jest odrzucany.

Rejestracja publiczna nadal nie tworzy administratora. Konta administracyjne
w testach są nadawane wyłącznie bezpośrednio w jednorazowej bazie. Brak
nowych kolumn lub migracji. Decyzje nie są weryfikacją tożsamości i nigdy
nie uruchamiają rzeczywistych wypłat.
