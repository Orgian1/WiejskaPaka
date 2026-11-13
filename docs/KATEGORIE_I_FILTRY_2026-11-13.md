# Kategorie, podkategorie i filtry WiejskaPaka

Gałąź: `codex/product-categories-filters-20261113`, utworzona z aktualnego
`codex/demo-finalization-fixes-20261112` (`6ef1d97a05685aac2c7f0569a998c82144978508`).

## Odbiór przez właściciela

Uruchom demo zgodnie z [instrukcją komputera i telefonu](ODBIOR_WLASCICIELA_2026-11-13.md),
z opcją `--full-demo` (włącza istniejące jednostki, zdjęcia i terminy dostaw).

1. Nad produktami, pod wyszukiwarką, jest jeden przewijany poziomo pasek:
   „Wszystkie” oraz 16 kategorii. Na telefonie przesuwaj go palcem. Wybrana
   kategoria ma ciemne tło i stan dostępności `aria-pressed`.
2. Wybierz kategorię. Pojawi się lista jej podkategorii, z możliwością pokazania
   wszystkich podkategorii. Po powrocie do „Wszystkie” lista znika.
3. Połącz kategorię, podkategorię i nazwę produktu. Zmieniaj „Dostępne teraz”
   i „Odbiór / Dostawa”. Każda zmiana zaczyna od pierwszej strony wyników;
   paginacja dotyczy całego przefiltrowanego zbioru.
4. „Najbliżej mnie” używa miejsca wybranego w istniejącym panelu lokalizacji,
   w tym lokalizacji zapisanej na koncie. Bez lokalizacji pokazuje przyciski
   ustawienia miejsca i GPS. GPS jest uruchamiany tylko po kliknięciu i zgodzie.
   Zmiana lub usunięcie miejsca odświeża sortowanie.
5. Wybierz produkt: szczegóły nadal rozwijają się pod całym odpowiednim rzędem.
   Serce pozostaje w prawym dolnym rogu zdjęcia i zapisuje ulubione na koncie.
   „Pokaż w katalogu” w ulubionych resetuje filtry, aby nie ukrywały wybranej oferty.
6. Zaloguj sprzedawcę. Formularz nowego produktu zawiera listy kategorii
   i podkategorii oraz opis. Dotychczasowe pola ceny, jednostki, ilości i zdjęcia
   są zachowane. Po dodaniu rozwiń „Edytuj produkt” w stanie magazynowym;
   popraw kategorię, podkategorię, opis, nazwę, cenę lub stan i zapisz.
   Zdjęcia istniejących ofert zmienia się w zachowanym panelu zdjęć.
7. Porównaj koszyk i wcześniejsze zamówienia przed i po zmianie kategorii.
   Nie powinny się zmienić ceny historycznych zamówień, jednostki ani ilości.

## Co dokładnie znaczą filtry

- „Wszystkie” oznacza brak ograniczenia kategorii. Nowy katalog może pokazać
  również produkty ze stanem zero; ich przyciski zakupu i koszyka są wyłączone.
- „Dostępne teraz” wymaga dodatniego stanu oraz obsługiwanego sposobu realizacji.
  Dla odbioru jest to aktywny punkt, a przy włączonym kalendarzu również aktualna
  lub przyszła data obecności. Dla dostawy wymagane jest aktywne okno sprzedawcy,
  jeśli włączono zatwierdzanie dostaw. Przy wyłączonej tej funkcji zachowano
  dotychczasową możliwość zamówienia dostawy. Filtr nie rezerwuje towaru.
- „Odbiór / Dostawa” dotyczy sposobów oferowanych przez sprzedawcę. Konkretny
  adres, termin i dostępność ilości są ponownie sprawdzane podczas zamówienia.
  Zgoda sprzedawcy i klienta na dostawę nadal działa według istniejących zasad.
- Odległość oznacza **linię prostą do najbliższego aktywnego punktu sprzedawcy
  z zapisanymi współrzędnymi**; przy kalendarzu uwzględnia również daty obecności.
  Nie jest trasą drogową, ETA ani obietnicą dostawy pod wskazany adres.
  Produkty bez takiego punktu są na końcu, z informacją o nieznanej odległości.
  Współrzędne są wysyłane w treści POST, bez zapisywania ich przez wyszukiwarkę.
  Dobrowolny zapis lokalizacji na koncie pozostaje oddzielną operacją.
- Wyszukiwanie tekstowe obejmuje nazwę produktu, ignoruje wielkość liter i polskie
  znaki diakrytyczne, a znaki `%` i `_` traktuje dosłownie. Kategorie, podkategorie,
  tekst, dostępność, sposób realizacji i odległość działają łącznie w backendzie.

## Dane i zgodność

Źródło słownika i stabilnych identyfikatorów: `backend/product_categories.py`.
Identyfikatory ASCII, np. `vegetables`, `vegetables-tomatoes`, są niezależne od
polskich etykiet. „Wszystkie” jest wyłącznie przyciskiem interfejsu, nie kategorią.
Słownik jest również zapisany w tabelach `product_categories` i
`product_subcategories`; klasyfikacja i opis są w `product_classifications`.
Para kategorii/podkategorii jest chroniona kluczem obcym oraz walidacją API.
Opis ma limit 2000 znaków i jest wyświetlany jako tekst, bez wykonywania HTML.

Publiczne endpointy: `GET /product-categories` oraz `POST /catalog/query`.
Zapisy korzystają z istniejących autoryzowanych `POST /products`,
`POST /products/with-photo` i `PATCH /products/mine/{id}`. Pola klasyfikacji są
opcjonalne dla starszych klientów API; brak rozpoznania daje „Pozostałe”.
Dotychczasowy `GET /catalog/search` zachowano dla zgodności starszych klientów.

Jednostka istniejącej oferty pozostaje niezmienna zgodnie z wcześniejszą ochroną
koszyków i zamówień. Nie przeliczamy sztuk na kilogramy ani starych stanów na
nowe jednostki. Nowe oferty wybierają jednostkę w istniejącym formularzu.
Edytor wysyła tylko zmienione pola. Zapis samego opisu lub kategorii nie odtwarza
starego stanu magazynowego, jeśli w międzyczasie zmieniło go zamówienie lub inne
urządzenie. Nie zmieniono prowizji, groszy, jednej opłaty dostawy za przesyłkę, automatycznej
akceptacji odbiorów po testowej płatności, PIN-ów ani ulubionych.

## Bezpieczna migracja

Nowy plik: `database/optional_product_categories.sql`. Manifest zawiera **45**
plików; wcześniejsze 44 SQL pozostają niezmienione. Migracja dodaje nowe tabele
z metadanymi i nie przebudowuje ani nie aktualizuje istniejących produktów,
zdjęć, cen, jednostek, stanów, koszyków czy zamówień.

Przyporządkowanie dotyczy wyłącznie pełnych nazw z jawnej listy `EXACT_NAMES`
(np. „Pomidory”, „Miód lipowy”, „Jaja kurze”). Nie stosujemy dopasowania fragmentów
ani modelu zgadującego. „Pomidory i ogórki”, nieznane nazwy marketingowe i inne nierozpoznane
oferty dostają `other` / `other-other`. Sprzedawca może je poprawić. Kolejny przebieg
migracji uzupełnia tylko brakujące rekordy, zachowując ręczne klasyfikacje i opisy.
Różnice obsługi wielkich liter Unicode w bazach mogą zostawić więcej pozycji
w „Pozostałe”; to celowo bezpieczniejsze niż przypisanie niepewnej kategorii.

SQLite: aplikacja lokalna tworzy i uzupełnia metadane w transakcji przy starcie.
Przed użyciem nowego kodu na trwałej lokalnej bazie zrób spójną kopię mechanizmem
backup API/snapshot, z uwzględnieniem WAL, i przećwicz odtworzenie.

PostgreSQL: operator najpierw wykonuje [procedurę kopii i próby na odtworzeniu](AKTUALIZACJA_VPS_ODBIOR_2026-11-13.md).
Na istniejącej bazie nie uruchamia całego bootstrapu. Po weryfikacji historii
migracji stosuje wyłącznie brakującą migrację na izolowanej kopii, z zatrzymaniem
na błędzie, i sprawdza liczbę produktów, kopie zdjęć, koszyki, zamówienia i salda.
Nowa aplikacja wymaga tabel klasyfikacji przy starcie; nie pomijaj tej kontroli.
Rola aplikacji potrzebuje odczytu słowników i odczytu/zapisu klasyfikacji, bez DDL.
Przykład dla roli ze wzorca preview, dopiero po sprawdzeniu nazwy przez operatora:

```sql
GRANT SELECT ON product_categories, product_subcategories TO wp_preview_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON product_classifications TO wp_preview_app;
```

Wycofanie kodu nie wymaga usuwania nowych tabel. Zachowaj metadane oraz aktualną
bazę; nie odtwarzaj starej kopii ponad nowymi zamówieniami. Stary kod może tworzyć
oferty bez klasyfikacji — przed powrotem do nowego kodu operator uzupełnia
brakujące rekordy migracją na kopii i sprawdza wynik. W tym zadaniu nie wykonywano
żadnych zmian na VPS ani danych produkcyjnych, nie zmieniano main i PayU.
