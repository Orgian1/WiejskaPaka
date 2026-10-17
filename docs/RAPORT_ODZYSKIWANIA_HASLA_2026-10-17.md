# Zapomniane hasło — pakiet lokalnego demo, 17.10.2026

Dodano formularz i lokalną skrzynkę wiadomości testowych. Link jest ważny
15 minut; w bazie znajduje się tylko SHA-256 tokenu. Potwierdzenie atomowo
zmienia hasło Argon2, cofa wszystkie sesje i pozostałe linki konta. Zwykła
zmiana hasła również unieważnia wcześniejsze linki. Odpowiedzi żądań nie
ujawniają istnienia konta; liczniki ograniczeń przetrwają restart procesu.
Nie ma rzeczywistej wysyłki e-mail. Poza launcherem funkcja jest opt-in,
a dla PostgreSQL pozostaje wyłączona.

Launcher tworzy prywatną, jednorazową skrzynkę. Regresja i pomocnicze launchery
nie dziedziczą jej konfiguracji. Odtwarzanie SQLite usuwa także odziedziczone
tokeny resetu. Audyt autoryzacji osobno oznacza dokładnie trzy trasy odzyskiwania,
bez rozszerzania wyjątków na inne endpointy. Testy potwierdzają, że sam adres
lub ID konta nie wystarcza do zmiany hasła.

Dodano testowy schemat PostgreSQL do jawnego manifestu oraz blokady sum
kontrolnych. Przegląd SQL: dwie tabele, klucz obcy użytkownika, indeks i
ograniczenie dodatniego licznika; brak usuwania danych, uprawnień lub połączeń
zewnętrznych. Nie wykonano migracji istniejącej bazy użytkownika. Dostarczony
schemat nie oznacza włączenia ani przetestowania resetu na PostgreSQL.

## Weryfikacja

**3637 PASS, 0 FAIL, 19 SKIP** dla 290 modułów Linux. Każdy moduł ma osobny
proces i bazę, grupy wykonywano równolegle. Dwa testy liczby plików manifestu
zaktualizowano po dodaniu 24. pliku SQL i uruchomiono ponownie. Podsumowanie
łączy najnowsze wyniki każdego modułu po sprawdzeniu identycznego odcisku
kodu aplikacji i zgodności skrótu każdego testowanego pliku z bieżącym plikiem.
Nie traktuje przebiegu ze zmienionymi testami jako niezmienionej monolitycznej
regresji. Oczyszczone wyniki: `audits/password_reset_2026-10-17.json`.

Zakres obejmuje ważność i jednorazowość kodu, ponowienie, obce konto, limity,
restart HTTP, jednoczesne potwierdzenia, odrzucenie tożsamości zamiast tokenu,
wycofanie zmian po błędzie, zachowanie zakupów i odtwarzanie kopii. Siedem
przypadków Node uruchamia rzeczywisty skrypt formularza: sukces, żądanie,
niezgodne hasła, utrata sieci, podwójne kliknięcie, zmiana konta i wyłączenie.
`node --check`, kompilacja Python i `git diff --check` bez błędów.

Dwa nowe testy rzeczywistego Chromium (390 i 1280 px) są pominięte lokalnie:
nie ma przeglądarki, a pobranie Playwright zwróciło nieprawidłowe archiwum.
Dołączono je do bramy przeglądarkowej CI. Skrypt Node nie zastępuje tych testów.
Nowych wyników Windows, PostgreSQL ani Chromium nie deklarujemy przed
zakończeniem odpowiedniego przebiegu CI.

## Pozostały zakres

Instrukcja i ograniczenia: `ODZYSKIWANIE_HASLA_TESTOWE.md`. Nadal wymagane są
rzeczywisty zweryfikowany kanał kontaktu, docelowa ochrona przed nadużyciami,
retencja wiadomości, PostgreSQL oraz potwierdzenie Windows ACL. Produkcyjne
kopie, płatności, hosting i domena nie zostały podłączone. Nie zmieniono `main`
ani danych użytkownika. Pakiet nie stanowi ukończenia wersji produkcyjnej.
