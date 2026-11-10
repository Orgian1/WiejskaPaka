# Końcowy wynik testów bez hostingu i prawdziwych płatności — 18.10.2026

Wszystkie zaplanowane kontrole istniejącego kodu zakończyły się sukcesem.
Badany commit: `e83feaf449f273a203bf82c0ab44b8f2ef90b0dc`.
Gałąź: `wiejskapaka-import`.
CI: https://github.com/Orgian1/WiejskaPaka/actions/runs/39138446651

## Potwierdzone wyniki

| Zestaw | Zaliczone | Błędy | Pominięte |
| --- | ---: | ---: | ---: |
| Pełna regresja Linux, 315/315 modułów | 3826 | 0 | 41 |
| Pełna regresja Windows, kompletna | 3811 | 0 | 56 |
| PostgreSQL, rzeczywista jednorazowa baza i ograniczona rola | 19 | 0 | 0 |
| Chromium/Linux, przeglądarka i prywatny podgląd | 36 | 0 | 0 |
| Szybka bramka Windows — podzbiór pełnej regresji | 80 | 0 | 0 |

Chromium zaliczył także rzeczywiste HTTP przy pięciu szerokościach ekranu.
Cztery końcowe zadania akceptacji HTTP: PASS. Minutowy test stabilności
lokalnego HTTP/SQLite: PASS, 461 rund, 4285 żądań, 10665 sprawdzeń
niezmienników. To powtarzane operacje, nie dodatkowe unikalne przypadki pytest.

Zestawy pokrywają się: nie sumować liczb między systemami, bramkami i
powtórzeniami. Szybkie 80 przypadków Windows wykonuje też pełna bramka.

## Pominięcia

41 pominięć w lokalnej regresji Linux dotyczy wyłącznie modułów wybranych
do natywnych bramek PostgreSQL i Chromium. Ich pełne listy uruchomienia
sprawdzono względem źródeł; obie natywne bramki mają zero pominięć.
W Linux nie były dostępne lokalny PostgreSQL i binarny Chromium, dlatego
wykonanie ich w izolowanym CI jest odrębnym, zweryfikowanym dowodem.

Raport Windows wykazuje 56 pominięć. Obejmuje warunkowe scenariusze
natywnych środowisk oraz ograniczenia platformy, m.in. uprawnienia POSIX
i symlinki. Nie oznaczono ich jako zaliczonych testów Windows. Testy
POSIX wykonuje pełny Linux; PostgreSQL i Chromium mają osobne bramki.

## Pochodzenie i spójność dowodów

Folder `audits/final_e83feaf_2026-10-18` zawiera oczyszczone raporty.
Cztery archiwa Actions pobrano i porównano z publikowanymi SHA-256.
Każdy natywny raport ma `complete=true`, `success=true`,
`sources_unchanged=true` i zgodne z lokalnym projektem odciski kodu,
źródeł testów, manifestu, zależności oraz workflow. Pełny Windows ma puste
listy niezaliczonych, niekompletnych i przekraczających czas modułów.

Pełny Linux również potwierdza kompletność i niezmienność źródeł.
Odciski akceptacji HTTP i stabilności porównano z właściwymi funkcjami
obliczania odcisku aplikacji. Nie przenoszono wyników starszego commitu.
Nie zapisano baz, kont, haseł, kluczy, surowych logów ani podpisanych URL.

## Granice zakończonego zakresu

Testowano istniejącą wersję demonstracyjną i testowe operacje. Nie podłączono
hostingu, domeny, Neon, rzeczywistych płatności, wypłat ani prawdziwej poczty.
Zakończenie testów nie zastępuje brakujących funkcji, audytu prawnego,
odbioru publicznego wdrożenia ani pomiaru 5000/500000 klientów dziennie.
Lista dalszego odbioru pozostaje w `ODBIOR_I_DALSZE_PRACE.md`.

Ten zapis dokumentuje koniec bieżącego pakietu testowania. Kolejna zmiana
kodu wymaga kontroli odpowiedniej do jej zakresu; obecnych wyników nie
przypisuje się automatycznie przyszłemu kodowi.
