# WiejskaPaka — integralność hasła i PIN-u, 17.10.2026

Punkt wyjścia: `0a3f92806a1c5f8401459f368aba2dbfd33955b3`.
Gałąź lokalna: `wiejskapaka-import`. Raport dotyczy czwartej paczki poprawek.

## Odtworzone problemy

Nowe 12 przypadków przed poprawką: **9 FAIL, 3 PASS**. To próby syntetycznie
uszkodzonych zapisów, odrębne od historycznych 37 błędów Windows.

- Nieprawidłowy format skrótu Argon2 mógł wywołać nieobsłużony
  `InvalidHashError`, odpowiedź 500 i wycofanie naliczenia nieudanej próby
  logowania lub potwierdzenia PIN-em.
- Potwierdzenie przesyłki sprawdzało tylko skrót pierwszego zamówienia.
  Uszkodzony lub inny poprawny skrót kolejnego zamówienia nie blokował
  potwierdzenia całej grupy.
- Przy różnych licznikach prób przesyłka pokazywała pozostały limit pierwszego
  zamówienia, chociaż blokada obowiązuje po wyczerpaniu limitu dowolnej pozycji.

## Poprawka

Logowanie i oba potwierdzenia odbioru obsługują także `InvalidHashError`.
Nieudane logowanie nadal daje ogólną odmowę 401, nalicza próbę i blokuje
następne żądanie kodem 429 po pięciu niepowodzeniach. Nie tworzy sesji.
Nieudana weryfikacja PIN-u nalicza próbę; po pięciu blokuje odbiór kodem 409.

Każde powiązane zamówienie musi zweryfikować podany PIN przed zmianą stanu
któregokolwiek zamówienia. Weryfikowana jest wartość PIN-u, a nie równość
skrótów: poprawny PIN z niezależnymi solami pozostaje akceptowany.
Limit widoczny klientowi wynika z największego licznika w grupie.
Weryfikacja Argon2 jest wykonywana dla każdego zamówienia; wydajność dużych
przesyłek pod obciążeniem wymaga pomiaru przed wdrożeniem.

Uszkodzone skróty pozostają niezmienione. Nie dopisano zastępczego PIN-u,
hasła ani mechanizmu obchodzącego weryfikację. Naprawa nie oznacza odzyskania
uszkodzonych danych; ich przyczyna wymaga osobnej analizy operacyjnej.

## Wykonane kontrole

Paczka obejmująca nowy moduł oraz istniejące testy magazynu zakupów,
odzyskiwania PIN-u i bezpieczeństwa sesji: **121 PASS, 0 FAIL, 0 SKIP**.
Po tej paczce dodano trzynasty nowy przypadek: poprawny odbiór całej grupy
przy osobno solonych skrótach tego samego PIN-u. Obejmuje go pełny przebieg.
Testy używają jednorazowego SQLite, syntetycznych kont i odizolowanego
środowiska bez produkcyjnych sekretów. Nowe przypadki działają przez ASGI
TestClient; osobny istniejący zestaw HTTP używa rzeczywistego lokalnego TCP.

## Pełna regresja końcowa

**3485 PASS, 0 FAIL, 17 SKIP — 3502 przypadki, 278/278 modułów.**
Raport kompletny, `success: true`, `sources_unchanged: true`.
Pełny przebieg rozpoczęto od początku po ostatniej zmianie kodu i testów.
Odcisk źródeł: `f3852da5b2672b2261418b15b0cca0b66692c16c2cec1a245defd990f6a3c99f`.
Osobna akceptacja rzeczywistego HTTP: **4/4 zadania PASS**; także bez zmiany
źródeł podczas przebiegu. Nie sumujemy jej z przypadkami pełnej regresji.

Zestawienie bez surowych logów i lokalnych ścieżek:
[`audits/regression_2026-10-17_v4_summary.json`](audits/regression_2026-10-17_v4_summary.json).

Pominięcia: PostgreSQL 15 przypadków, mobilny test offline 1 i rozszerzony test
ról offline 1. Nie są traktowane jako zaliczenia. Wzrost względem paczki v3
wynika z 13 nowych przypadków; nie dowodzi odtworzenia wszystkich lokalnych
modułów Windows użytkownika. `git diff --check`: PASS.

## Zakres i ograniczenia

Natywny Windows, PostgreSQL i Chromium nadal wymagają osobnego sprawdzenia.
19 historycznych modułów lokalnych pozostaje poza repozytorium. Nie ma
podstaw do deklarowania zgodności z kompletnym lokalnym raportem użytkownika.
Pełny audyt bezpieczeństwa, RLS, zgodności konsumenckiej oraz procedur kopii
i odtwarzania pozostaje do wykonania. Aplikacja nadal nie jest gotowa do
wdrożenia produkcyjnego.

Zachowano całkowite grosze, pojedynczą opłatę za przesyłkę, odbiór PIN-em,
pełny zwrot przy winie dostawcy i prywatność telefonów. Nie podłączano
płatności rzeczywistych, domeny ani hostingu. Nie zmieniano `main`.
Zapis GitHub pozostaje niedostępny po wcześniejszym 403; poprawki przekazano
w lokalnym commicie i zbiorczej paczce z instrukcją bezpiecznego łączenia.
Ponowny odczyt referencji z GitHub potwierdził bazę
`c5e1b49d337b8641eec2933321d750017b788168`; zdalna gałąź nie zawiera lokalnych
czterech serii poprawek. Nie wykonano ponownej próby zapisu bez nowych uprawnień.
