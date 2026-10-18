# Trwałość zakupu PostgreSQL po restarcie aplikacji — 18.10.2026

Dwa dodatkowe scenariusze natywne sprawdzają przygotowanie do stałej wersji
testowej, bez hostingu i prawdziwych płatności. Nie zmieniono kodu aplikacji
ani reguł sprzedaży. Rozszerzono testy i minimalną liczebność bramki PostgreSQL
z 19 do 21 przypadków.

## Co jest sprawdzane

Każdy scenariusz otrzymuje własną losową bazę PostgreSQL, ograniczoną rolę,
osobny klucz szyfrowania i proces Uvicorn na loopback. Nie korzysta ze wspólnej
bazy testów celowo naruszających zaszyfrowane rekordy. Testy nie otwierają,
nie migrują i nie usuwają istniejących baz użytkownika.

1. Zakup pojedynczego produktu z kluczem ponowienia żądania.
2. Zakup przesyłki z dwoma produktami, jedną opłatą za dostawę i testowym
   potwierdzeniem zapłaty dla pozycji.

W obu przypadkach aplikacja jest zatrzymywana, a następnie uruchamiana na
tej samej bazie i z tym samym kluczem. Odbiór obejmuje:

- zachowanie istniejącej sesji klienta;
- identyczną odpowiedź po ponowieniu zakupu, razem z pierwotnym PIN-em;
- niezmienione identyfikatory, kwoty, statusy i stan magazynowy;
- zachowanie stanu testowego rozliczenia i zaszyfrowanej odpowiedzi;
- identyczne pierwotne warunki zakupu;
- odmowę zmienionego adresu z tym samym kluczem (409), bez nowych zamówień.

Stary proces jest kończony i oczekiwany przed startem nowego. Każdy proces
ma ograniczony czas gotowości, a fixture sprząta proces, nową bazę i rolę
również przy błędzie. Dotychczasowe testy nadal rozpakowują klienta i parametry
połączenia w tej samej postaci; restart jest dodatkową funkcją kontekstu.

## Granice dowodu

To restart procesu aplikacji, nie restart PostgreSQL, awaria dysku,
odtworzenie backupu ani utrata zasilania. Nie dowodzi wysokiej dostępności
lub obsługi docelowej liczby klientów. Testowe potwierdzenie zapłaty nie
uruchamia rzeczywistego operatora płatności.

## Weryfikacja

Lokalnie: 37 zaliczonych testów reportera CI i przeglądu schematu; 17 przypadków
w module natywnej integracji PostgreSQL pominięto z powodu braku lokalnego DSN.
Nie uznano ich za zaliczone lokalnie. Wszystkie 21 przypadków bramki PostgreSQL
muszą przejść bez pominięć na jednorazowym serwerze CI; wynik jest osobnym
dowodem powiązanym z konkretnym commitem.

Poprzedni zamknięty pakiet pełnej regresji dotyczy commitu e83feaf i pozostaje
opisany w WYNIK_KONCOWY_TESTOW_BEZ_HOSTINGU_2026-10-18.md. Tych wyników nie
przypisuje się automatycznie rozszerzonemu zestawowi testów.
