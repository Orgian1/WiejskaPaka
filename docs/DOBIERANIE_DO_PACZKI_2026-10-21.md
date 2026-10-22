# Dobieranie produktów do jednej paczki

Przy dodawaniu produktu do koszyka i przed zatwierdzeniem zakupu bezpośredniego klient otrzymuje propozycję „Dobierz do jednej paczki od tego sprzedawcy”. Okno korzysta z rzeczywistego katalogu, filtruje produkty po sprzedawcy, pomija produkt wyjściowy i pokazuje dostępne oferty, ceny, jednostki oraz ilości. Wyniki są stronicowane po 24 pozycje. Jeśli nie ma innych ofert, okno nie jest otwierane.

Dobór przenosi zakup do wspólnego koszyka sprzedawcy. Dodawane ilości uwzględniają pozycje, które już były w koszyku. Przed zapisem sprawdzany jest limit ilości; końcowa kontrola dostępności i wycena pozostają po stronie API. Produkty innych sprzedawców pozostają w koszyku i nie trafiają do tej przesyłki.

Klient zatwierdza paczkę w dotychczasowym checkout. Jedna opłata za przesyłkę jest naliczana według istniejącej polityki dostaw. Propozycja pojawia się przed ostatecznym zakupem, ponieważ wcześniej zapisane zamówienia nie są dołączane do nowych zakupów. Samo otwarcie okna nie rezerwuje towaru i nie tworzy zamówienia.

Można pominąć propozycję albo wrócić do produktów. Po dobraniu towarów przycisk kieruje do koszyka wybranego sprzedawcy. Zmiana konta zamyka okno i unieważnia opóźnione odpowiedzi. Podczas zapisu koszyka przyciski są blokowane. Dane tego okna nie są utrwalane w pamięci przeglądarki.

## Walidacja lokalna

- 26 testów interfejsu, izolacji kont i ochrony przed ponownym zakupem: PASS.
- 6 testów HTTP resetowania hasła: PASS.
- 3 testy zasad naliczania dostawy: PASS.
- Kontrola składni JavaScript i `git diff --check`: PASS.

## Scenariusze przeglądarkowe

Istniejący test katalogu rozszerzono o cztery scenariusze: dodawanie do koszyka lub zakup bezpośredni, każdy na ekranie 320 i 1280 pikseli. Weryfikują dwie pozycje w jednej przesyłce, poprawne ilości, jedną opłatę 501 gr, sumę 1498 gr i brak zamówienia przed zatwierdzeniem.

Pierwszy przebieg CI potwierdził wszystkie cztery scenariusze. Wykrył także kolizję testu wyszukiwania sprzedawców z asynchroniczną obsługą nowego okna oraz pojedynczy timeout uruchamiania testowego serwera na Windowsie. Obsługę pustych propozycji i oczekiwanie na zakończenie dodawania poprawiono. Ponowny przebieg zakończył się powodzeniem w Chromium, PostgreSQL 16 i 17 oraz szybkim zestawie Windows. Raporty zapisano w `docs/audits/same_package_2026-10-21/native_3626166/`. Pełna izolowana regresja Windows została przerwana po 1500 sekundach przez limit nadrzędnego procesu. Nie ma końcowego wyniku i nie jest oznaczona jako zaliczona. 22.10.2026 zwiększono limit do 2100 sekund, limit zadania do 45 minut oraz dodano zapis bezpiecznego częściowego postępu przy timeout. 41 testów mechanizmu CI przeszło lokalnie. Wymagany jest nowy pełny przebieg Windows. Przebieg dotyczy commitu `36261663ec288e6b1a9f27dff70ffabe47017427`:

https://github.com/Orgian1/WiejskaPaka/actions/runs/39665127913

Draft PR: https://github.com/Orgian1/WiejskaPaka/pull/24

Zmiany nie zostały wdrożone na VPS. Podgląd HTML korzysta z przykładowych danych i symulacji zakupów; nie zastępuje testów API.

## Ponowny start Windows — 22.10.2026

Przebieg `39774607878` zaliczył Chromium, PostgreSQL 16 i 17 oraz osobny szybki zestaw Windows. Zadanie pełnej regresji zatrzymało się w powtórzonym zestawie wstępnym: 79/80, timeout gotowości testowego serwera HTTP w `test_sqlite_snapshot.py`. Pełna regresja nie została uruchomiona. Dowód zapisano w `native_ab96f95/windows-summary.json`.

Zwiększono budżet gotowości jednorazowego serwera testowego z 20 do 60 sekund. Sprawdzanie śmierci procesu nadal kończy oczekiwanie natychmiast, a limit jest liczony czasem monotonicznym. Zmiana dotyczy wyłącznie testów. Wymagany jest nowy przebieg Windows.

## Pełna regresja Windows — wynik i korekta testów

Przebieg `39776194507` zakończył pełną regresję: 4367 testów, 4192 PASS, 2 FAIL, 173 SKIP. Raport: `native_a9f33c1/windows-summary.json`. Dwa nieaktualne testy oczekiwały bezpośredniego sąsiedztwa walidacji ilości z blokadą checkout oraz dawnego 20-sekundowego budżetu startu serwera.

Test blokady nadal wymaga wywołania `requireResolvedCheckout()` na początku obsługi dodawania do koszyka. Test gotowości sprawdza teraz udany start po ponad 20 sekundach oraz granicę 60 sekund, a nadal weryfikuje natychmiastowe zakończenie po śmierci procesu i sprzątanie po błędzie konsumenta. Kod aplikacji nie został zmieniony w tej korekcie. Wymagany jest kolejny pełny przebieg Windows.
