# WiejskaPaka — zgodność zwrotu z zamknięciem zamówienia, 17.10.2026

Punkt wyjścia: `83c58f77b01ace0cac77957c846a8ff97c332003`.
Gałąź lokalna: `wiejskapaka-import`. Ósma zbiorcza paczka napraw.
Prace lokalne, bez prób połączenia z GitHubem, zgodnie z poleceniem użytkownika.

## Odtworzony problem

Historia płatności mogła być zgodna z automatem i kwotami, lecz wskazywać
inną przyczynę zwrotu niż zamknięcie zamówienia. Ponowienie mogło też zgłosić
sukces przy usuniętym lub powtórzonym wpisie zamknięcia albo wpisie z błędnym
poprzednim statusem lub użytkownikiem.

Nowe próby przed poprawką: **19 FAIL, 5 PASS — 24 przypadki**.
To odrębne testy celowo uszkodzonych danych syntetycznych, nie odtworzenie
historycznych 37 błędów Windows ani dowód uszkodzenia rzeczywistych zakupów.
Jedną z odrzuconych prób chroniła już wcześniejsza kontrola identyfikatora
i typu powtarzanego zdarzenia; cztery dodatnie przypadki potwierdziły działanie
poprawnych ponowień także przed zmianą.

## Zmiana

Zakończony zwrot musi zgadzać się z bieżącym zamówieniem i zapisanym wpisem
jego zamknięcia. Anulowanie wymaga zdarzenia zwrotu na prośbę klienta,
przejścia ze stanu oczekiwania na płatność oraz wpisu właściwego dla pojedynczego
zakupu lub przesyłki, wykonanego przez klienta będącego właścicielem zamówienia.

Nieudana dostawa wymaga realizacji na adres, zdarzenia zwrotu z winy dostawcy,
przejścia ze stanu w drodze i wpisu wykonanego przez właściwego rolnika.
Tak działa istniejący interfejs zgłoszenia winy dostawcy; nie zmieniono ról.
Wymagany jest dokładnie jeden wpis zamknięcia do aktualnego stanu i jeden
odpowiadający mu zwrot. Niezgodność daje odmowę 409 przed potwierdzeniem
ponowienia lub zapisem kolejnego zdarzenia.

Kontrola obejmuje ponowienia anulowania zakupów i przesyłek oraz zwrotów
za winę dostawcy, w tym pojedyncze zamówienie obsługiwane przez API zdarzeń
płatności. Zachowano wcześniejsze kontrole kwot, historii, sesji i uprawnień.
Pozycje nieopłacone w częściowo opłaconej przesyłce nadal nie dostają zwrotu.

Nie zmieniono schematu, kluczy ani zapisanych zakupów. Brakujące wpisy nie są
dopisywane automatycznie; istniejące sprzeczne dane wymagają wyjaśnienia.

## Potwierdzone kontrole

- Paczka regresji: **71 PASS, 0 FAIL, 0 SKIP** w czterech modułach.
- Nowy moduł obejmuje cztery ścieżki: anulowanie pojedynczego zakupu i przesyłki
  oraz zwrot za winę dostawcy dla pojedynczego zakupu i przesyłki.
- Dla każdej ścieżki sprawdza poprawne ponowienie oraz pięć niespójności:
  przyczynę zwrotu, brak zamknięcia, poprzedni status, autora i duplikat zamknięcia.
- Odrzucone próby porównują hash danych tabel testowej bazy przed i po żądaniu.
  Poprawne ponowienia zwracają tę samą kwotę i również nie zmieniają bazy.
- Wcześniejsze testy nadal sprawdzają historię płatności, spójność kwot,
  częściowo opłacone przesyłki i pełny zwrot przy winie dostawcy.

Nowe próby działają przez ASGI TestClient na danych syntetycznych.
Moduły uruchamiane są w osobnych procesach z jednorazowym SQLite,
bez produkcyjnych sekretów i adresów baz. Płatności są symulowane.

## Pełna regresja końcowa

**3561 PASS, 0 FAIL, 17 SKIP — 3578 przypadków, 282/282 modułów.**
Raport kompletny, `success: true`, `sources_unchanged: true`.
Przebieg wykonano od początku po ostatniej zmianie kodu i testów, bez wznowienia.
Odcisk źródeł: `16055fe6d3ab27a4bb590518dd54b99562c3fd1d91418b9376f7b919fbe5d603`.

Osobna akceptacja rzeczywistego TCP HTTP: **4/4 zadania PASS**, także bez zmiany
źródeł. Obejmuje zakup, dostawę, pełny zwrot, koszyk wielu rolników, prywatność
oraz pojedynczą opłatę za przesyłkę. Nie sumujemy jej z przypadkami pytest.
Zestawienie bez surowych logów i lokalnych ścieżek:
[`audits/regression_2026-10-17_v8_summary.json`](audits/regression_2026-10-17_v8_summary.json).

Pominięcia: PostgreSQL 15 przypadków, mobilny test offline 1 i rozszerzony test
ról offline 1. Nie są zaliczeniami. Przyrost względem v7 wynika z 24 nowych
przypadków; nie oznacza wykonania historycznych lokalnych modułów Windows.
`git diff --check`: PASS.

## Pozostałe ograniczenia

Spójny zestaw jednocześnie sfałszowanych zapisów nie jest wykrywany
kryptograficznie. Kontrola nie certyfikuje tożsamości historycznego autora
ani dat; porównuje zapisane dane. Nie jest pełnym audytem wszystkich przejść
zamówienia, raportów odczytowych ani narzędziem odtwarzania księgowości.
Zmiany ról w czasie i szersza analiza śladu audytowego wymagają dalszej oceny.

Natywny Windows, PostgreSQL i Chromium pozostają do weryfikacji. 19 historycznych
lokalnych modułów pozostaje poza repozytorium i nie zostało tu uruchomionych.
Nadal wymagane są pełny audyt bezpieczeństwa i RLS, weryfikacja zgodności
konsumenckiej, wydajności oraz procedur kopii i odtwarzania.
Aplikacja nie jest gotowa do produkcji.

Zachowano całkowite grosze, opłatę raz na przesyłkę, PIN, pełny zwrot przy winie
dostawcy i prywatność telefonów. Nie podłączano domeny, hostingu ani rzeczywistych
płatności. `main` pozostaje bez zmian. Nowy commit i paczka są lokalne;
nie wykonywano prób odczytu ani zapisu GitHub.
