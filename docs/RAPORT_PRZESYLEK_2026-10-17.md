# WiejskaPaka — spójność powiązań przesyłek, 17.10.2026

Punkt wyjścia: `e334e45d6f6519cd9e078653ce0ace09c98a1ae2`.
Gałąź lokalna: `wiejskapaka-import`. Piąta zbiorcza paczka napraw.

## Odtworzony problem

W sześciu operacjach modyfikujących przesyłki uprawnienia były sprawdzane
względem grupy, ale nie porównywano klienta, rolnika i sposobu realizacji
każdego zamówienia z danymi grupy. Niespójne powiązanie w bazie mogło więc
pozwolić uprawnionemu do grupy użytkownikowi zmienić zamówienie należące
do innego klienta lub rolnika.

Nowe testy przed poprawką: **18 FAIL, 0 PASS**. To oddzielne, syntetyczne
próby uszkodzenia zapisu, nie odtworzenie historycznych 37 błędów Windows.
Nie wykazano publicznego endpointu pozwalającego użytkownikowi tworzyć takie
powiązania; problem dotyczy bezpiecznej odmowy przy niespójnej zapisanej bazie.

## Poprawka

Wspólna kontrola porównuje `buyer_id`, `farmer_id` i `fulfillment` każdego
powiązanego zamówienia z grupą. Działa po odczycie grupy i zamówień wewnątrz
istniejącej transakcji, przed zmianą danych, naliczeniem prób PIN-u lub zwrotem.
Niespójność daje ogólne 409 bez identyfikatorów cudzych użytkowników.

Kontrolą objęto:

- potwierdzenie odbioru PIN-em;
- anulowanie nieopłaconej przesyłki;
- anulowanie z symulowanym zwrotem;
- przypisanie dostawcy;
- wysyłkę;
- pełny symulowany zwrot za brak realizacji z winy dostawcy.

Nie zmieniono schematu ani nie naprawiano zapisanych powiązań automatycznie.
Niespójny zakup wymaga sprawdzenia; aplikacja nie próbuje zgadywać właściciela.
Nie zastąpiono wcześniejszej kontroli sesji, roli, statusu, PIN-u i płatności.
Kod współdzielony obejmuje SQLite i PostgreSQL, ale natywny PostgreSQL nie
był tu uruchomiony; same klauzule blokad nie stanowią dowodu jego działania.

## Testy wykonane

Nowy moduł obejmuje 6 operacji razy 3 niespójności, łącznie 18 prób.
Każda porównuje hash całej jednorazowej bazy przed i po odrzuconej operacji.
Obejmuje to zamówienia, stan magazynowy, przypisania, próby PIN-u, zdarzenia
i rozliczenia. Poprawka nie usuwa ani nie nadpisuje uszkodzonego zapisu.
Próby używają ASGI TestClient oraz syntetycznych kont; nie używają produkcji.

Paczka regresji: **47 PASS, 0 FAIL, 0 SKIP** w pięciu modułach. Obejmuje nowe
próby oraz istniejące testy integralności finansowej, PIN-u i anulowania.
Zewnętrzne usługi i produkcyjne sekrety nie były przekazywane do procesów
testowych. Płatności są wyłącznie symulowane, a bazy SQLite jednorazowe.

## Pełna regresja końcowa

**3503 PASS, 0 FAIL, 17 SKIP — 3520 przypadków, 279/279 modułów.**
Raport jest kompletny, `success: true`, `sources_unchanged: true`.
Przebieg rozpoczęto od początku po ostatniej zmianie kodu i testów.
Pierwszy proces pozostawił checkpoint 277/279 bez końcowego podsumowania.
Dwa ostatnie moduły wykonano przez `--resume`: runner zweryfikował zgodność
odcisku aplikacji, planu i hashy wcześniej wykonanych modułów. Nie zmieniano
kodu, testów ani ich helperów między częściami; nie użyto wyników starszej paczki.
Odcisk źródeł: `8a703b3f2376b75469ce6f8ab985ad0920c4cc9c69107631f5d56a54f06a07d8`.

Osobna akceptacja rzeczywistego TCP HTTP: **4/4 zadania PASS**, także bez
zmiany źródeł. Obejmuje zakup, dostawę, pełny zwrot, koszyk wielu rolników,
prywatność i pojedynczą opłatę za przesyłkę. Nie sumujemy tych zadań z pytest.
Zestawienie bez surowych logów i lokalnych ścieżek:
[`audits/regression_2026-10-17_v5_summary.json`](audits/regression_2026-10-17_v5_summary.json).

Pominięte przypadki: PostgreSQL 15, mobilny test offline 1 i rozszerzony test
ról offline 1. Nie są zaliczeniami. Wzrost względem v4 wynika z 18 nowych
przypadków, nie z odtworzenia brakujących lokalnych modułów Windows.
`git diff --check`: PASS.

## Pozostałe ograniczenia

Sprawdzono tę granicę operacji przesyłek, nie kompletną odporność bazy na
dowolną korupcję. Nie rozszerzano automatycznej naprawy historycznych danych.
Natywny Windows, PostgreSQL i Chromium pozostają do weryfikacji.
19 historycznych modułów lokalnych nie jest częścią repozytorium i nie zostało
tu uruchomionych. Nadal potrzebne są pełny audyt bezpieczeństwa i RLS,
weryfikacja zgodności konsumenckiej, wydajności dużych przesyłek oraz procedur
kopii i odtwarzania. Aplikacja nie jest gotowa do produkcji.

Zachowano całkowite grosze, opłatę za dostawę raz na przesyłkę, odbiór PIN-em,
pełny zwrot przy winie dostawcy i prywatność telefonów. Nie podłączano domeny,
hostingu ani rzeczywistych płatności. `main` pozostaje bez zmian.

Ponowny odczyt gałęzi GitHub potwierdził bazę
`c5e1b49d337b8641eec2933321d750017b788168`. Zapis integracji pozostaje
niepotwierdzony po wcześniejszym błędzie 403; nie ponawiano go bez nowych
uprawnień. Lokalne poprawki są przekazywane w zbiorczym bundle i patchu.
