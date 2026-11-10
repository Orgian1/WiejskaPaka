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


## Końcowe potwierdzenie rozszerzonego zestawu

Wszystkie bramki zakończone sukcesem dla
`9f5fe158fcabf828c9e611d4decf0c65875eabbc`.
CI: https://github.com/Orgian1/WiejskaPaka/actions/runs/39141137034

| Zestaw | Zaliczone | Błędy | Pominięte |
| --- | ---: | ---: | ---: |
| Pełny Linux, 315/315 modułów | 3826 | 0 | 43 |
| Pełny Windows, kompletny | 3811 | 0 | 58 |
| PostgreSQL z restartami API | 21 | 0 | 0 |
| Chromium/Linux i prywatny podgląd | 36 | 0 | 0 |
| Szybki Windows, podzbiór pełnego zestawu | 80 | 0 | 0 |

Łączny rozmiar pełnej regresji wynosi 3869 przypadków na każdym systemie.
Nie sumować liczb między systemami i bramkami. Wszystkie 43 lokalne pominięcia
Linux należą do modułów wykonanych w osobnych natywnych bramkach. Pominięcia
Windows obejmują też warunki platformy, w tym POSIX i symlinki; nie uznano
ich za zaliczone na Windows. Bramka Chromium zaliczyła ponadto rzeczywiste
HTTP przy pięciu szerokościach ekranu.

Raporty znajdują się w `audits/restart_9f5fe15_2026-10-18`. Cztery archiwa
Actions zweryfikowano przez SHA-256, a raporty przez odciski kodu, testów,
manifestu, zależności i workflow. Wszystkie natywne raporty mają complete,
success i sources_unchanged równe true. Pełny Linux również potwierdza
kompletność i niezmienność źródeł. Windows nie zgłasza modułów błędnych,
niekompletnych ani przekraczających czas.

Porównanie git potwierdziło brak zmian w backend, web i database względem
zamkniętej wersji e83feaf. Rozszerzenie dotyczy testów oraz ich bramki CI.
Wcześniejsza akceptacja HTTP i stabilność są przypisane do tamtej wersji;
nie dodano ich liczników do obecnej regresji.

Etap potwierdzenia trwałości zakupów po restarcie aplikacji jest zakończony.
Nie jest to potwierdzenie odtworzenia PostgreSQL z backupu, awarii sprzętu,
wydajności docelowego hostingu ani dopuszczenie rzeczywistych płatności.
