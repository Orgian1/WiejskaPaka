# Kategorie i filtry produktów — raport wykonania

Repozytorium: `Orgian1/WiejskaPaka`.
Nowa gałąź: `codex/product-categories-filters-20261113`.
Baza sprawdzona na GitHubie przed pracą:
`6ef1d97a05685aac2c7f0569a998c82144978508`
(`codex/demo-finalization-fixes-20261112`).
Commit kodu: `b986571e27683416a9888946b4925b97dcd25680`.
Końcowy commit raportu i wynik push podano w odpowiedzi po tej operacji.

## Wykonane zmiany

1. Dodano 16 kategorii ze stabilnymi identyfikatorami, podkategorie z wymaganej
   listy i jeden przycisk „Wszystkie”. Kategorie są w jednym poziomym pasku
   przewijanym na dotyku; aktywna ma wyróżnienie i `aria-pressed`.
   Lista podkategorii pojawia się dopiero po wyborze głównej kategorii.
2. Dodano słowniki i powiązania w bazie. Opis oferty jest przechowywany razem
   z klasyfikacją w osobnej tabeli, bez przebudowy istniejących produktów.
3. Formularz sprzedawcy pozwala wybrać kategorię/podkategorię z list i podać opis;
   zachowano istniejącą cenę, jednostkę, ilość i dodawanie zdjęcia. W stanie
   magazynowym dodano edycję istniejącej oferty. Edytor wysyła **tylko zmienione
   pola**, aby zapis opisu nie nadpisywał stanu zmienionego w międzyczasie.
4. Backend łączy kategorię, podkategorię, tekst, stan, sposób realizacji,
   wybranego sprzedawcę, istniejące zakresy cen oraz sortowanie i paginację.
   Nowy `POST /catalog/query` nie umieszcza współrzędnych w URL. Zachowano
   dotychczasowy `GET /catalog/search` dla starszych klientów.
5. „Dostępne teraz” sprawdza stan i możliwość realizacji według aktywnych
   punktów/dat lub okien dostaw. Konkretna rezerwacja i adres są ponownie
   weryfikowane przy zamówieniu. Brak towaru jest widoczny w pełnym katalogu,
   z wyłączonymi przyciskami zamówienia i dodania do koszyka.
6. „Najbliżej mnie” używa zapisanej/wybranej lokalizacji lub GPS za zgodą.
   Bez lokalizacji pokazuje działania jej ustawienia. Rzeczywista odległość
   w linii prostej jest liczona do najbliższego aktywnego punktu sprzedawcy
   z koordynatami i odpowiednią datą, gdy kalendarz jest włączony. Brakujące
   odległości są oznaczone jako nieznane i sortowane na końcu.
7. Zachowano karty w rzędach, szczegóły pod całym rzędem oraz serca na zdjęciach.
   „Pokaż w katalogu” z ulubionych czyści filtry, aby wybrana oferta była widoczna.
   Zmiana/usunięcie lokalizacji odświeża sortowanie. Nie zmieniano zasad
   finansowych, prowizji, jednej opłaty przesyłki, przyjmowania odbiorów ani PIN-ów.

## Migracja i zachowanie danych

Nowa migracja `database/optional_product_categories.sql` dodaje tylko:
`product_categories`, `product_subcategories`, `product_classifications` i indeks.
Wcześniejsze **44 pliki SQL** pozostały niezmienione; manifest obejmuje teraz **45**.

Uzupełnienie starych ofert opiera się na dokładnych pełnych nazwach z jawnej listy.
Mieszanki i niepewne nazwy trafiają do „Pozostałe”; sprzedawca może poprawić wybór.
Nie stosowano klasyfikacji heurystycznej. Powtórne wykonanie zachowuje istniejące
ręczne przypisania i opisy. Walidacja API i FK chronią parę kategorii/podkategorii.

Test migracji SQLite porównuje niezmienione rekordy produktów, cen, stanów,
zdjęć BLOB i zamówień oraz sprawdza FK. Natywny test PostgreSQL odtwarza brak
klasyfikacji w istniejących produktach, stosuje migrację, porównuje pełne rekordy
i sprawdza powtórkę bez utraty ręcznej poprawki. Scenariusze API potwierdzają
zachowanie wcześniejszych zamówień i pozycji koszyka po zmianie klasyfikacji.

Instrukcja i plan aktualizacji uprawnień oraz wycofania:
[Kategorie i filtry](KATEGORIE_I_FILTRY_2026-11-13.md) oraz
[procedura VPS](AKTUALIZACJA_VPS_ODBIOR_2026-11-13.md).
Nie wykonywano migracji ani wdrożenia na VPS.

## Wyniki końcowe

| Zestaw | PASS | FAIL | SKIP |
| --- | ---: | ---: | ---: |
| Pełna izolowana regresja SQLite i pozostałych modułów — 404 moduły | 4948 | 0 | 108 |
| Pełna natywna bramka PostgreSQL 17.11 | 105 | 0 | 0 |
| Rozszerzony zestaw przeglądarkowy | 118 | 0 | 0 |
| Osobna kontrola zdjęć w Chromium | 2 | 0 | 0 |

Wszystkie cztery części pełnej regresji są kompletne i mają `success=true`
oraz `sources_unchanged=true`. Obie natywne bramki również potwierdziły zgodność
hashy źródeł, testów i zależności. Zestaw przeglądarkowy wykonano z budżetem
1200 sekund dla pełnego kohortu, bez pomijania przypadków ani asercji.

108 pominięć pełnego zestawu to: 105 przypadków PostgreSQL wykonanych osobno,
jeden rozszerzony test ról zaliczony osobno w przeglądarce oraz dwa przypadki
odmowy uprawnień na platformach innych niż POSIX, niewykonane na Linuksie.
Nie zaliczano pominięć do PASS.

Przeglądarka: rzeczywiste przepływy kategorii, dodania produktu ze zdjęciem,
edycji przy równoległej zmianie stanu, filtrów, lokalizacji, ulubionych, rzędów
oraz koszyka sprawdzono przy **320, 768 i 1280 px**. Ponadto standardowa kontrola
HTTP/Chromium przy **320, 360, 390, 768 i 1280 px** zakończyła się sukcesem.
Manifest i sumy 45 SQL, niezmienność poprzednich 44 SQL, składnia zmienionego JS
oraz `git diff --check` przeszły. Nie pozostaje znany błąd nowej funkcji
w wykonanych scenariuszach.

Zestawy mogą zawierać te same przypadki; ich liczb nie należy sumować jako
unikalnych testów. Dowody bez surowych logów i poświadczeń:
`docs/audits/categories_filters_20261113/`.

Pierwszy przebieg roboczy wykrył nieaktualny rejestr publicznych endpointów
oraz test formularza Kontakt traktujący odczyt POST jako zapis. Uzupełniono
rejestr o dokładne metody/ścieżki nowych publicznych odczytów; dodano testy
odrzucające szersze wyjątki. Test Kontakt nadal blokuje zapisy i sprawdza brak
wysyłania e-maila/treści formularza w zapytaniach katalogu. Nie wyłączano testów.
Nowe dane klasyfikacji dodano do uproszczonej bazy testu edycji produktu.
Końcowe wyniki dotyczą ponownego pełnego przebiegu na ustabilizowanym kodzie.

## Odbiór i ograniczenia

- Ręczny odbiór: [lista kategorii/filtrów](KATEGORIE_I_FILTRY_2026-11-13.md).
  [Instrukcja uruchomienia](ODBIOR_WLASCICIELA_2026-11-13.md) wskazuje nową gałąź
  i zachowuje opcjonalny HTTPS do testowania tej samej instancji przez telefon.
- Fizyczny telefon i Windows nie były dostępne do ręcznego testu. Testy mobilne
  używają Chromium z emulacją ekranu, dotyku i lokalizacji. Sprawdzono też zrzuty
  publicznego katalogu przy szerokościach 320, 768 i 1280 px: 17 przycisków
  kategorii, przewijanie paska, poprawne rzędy i brak overflow całej strony.
- Nieznane klasyfikacje celowo pozostają w „Pozostałe” do przeglądu sprzedawcy.
  Nie importowano nowych zdjęć ani nie zmieniano istniejących jednostek sprzedaży.
- Odległość dotyczy punktu odbioru i linii prostej; nie jest odległością drogową
  ani potwierdzeniem obsługi konkretnego adresu dostawy. Braków nie uzupełniamy
  zgadywanymi współrzędnymi. Nowe filtry nie wymagają zewnętrznego geokodera;
  wcześniejsza blokada publicznego Photon w proxy pozostaje niezależnym ograniczeniem.

Nie zmieniano main, gałęzi bazowej na GitHubie, działającego VPS, danych
produkcyjnych ani prawdziwych płatności. Nie publikowano środowiska.
