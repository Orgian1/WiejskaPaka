# Synchronizacja kopii SQLite i diagnostyka Windows — 18.10.2026

Poprzedni przebieg `39053020840` zakończył Windows wynikiem 3631 PASS,
3 FAIL i 24 SKIP. Raport zawierał liczniki, lecz nie nazwy błędnych modułów,
więc nie przypisujemy wstecz konkretnych trzech przypadków bez dowodu.
PostgreSQL miał 15 PASS, Chromium 9 PASS i poprawną kontrolę pięciu viewportów.

Zmieniono końcowe otwarcie nowo utworzonej kopii SQLite z `rb` na `r+b` przed
`os.fsync`. Synchronizacja bufora Windows wymaga uchwytu z uprawnieniem zapisu.
Źródłowa baza nadal jest otwierana tylko do odczytu; zmiana dotyczy wyłącznie
własnego pliku docelowego. Nie wyłączono synchronizacji ani kontroli integralności.

Nowy test wymusza prawo zapisu na każdym zwykłym pliku synchronizowanym przez
operację: zapis zera bajtów nie zmienia danych, a odrzuca uchwyt tylko do odczytu.
Jest to test ograniczenia systemowego wykonywany także na Linux, a nie dowód
natywnego Windows. Kontrole zakupów, sesji, jednej opłaty i odmowy nadpisania
pozostają aktywne.

## Diagnostyka i brama

Windows wykonuje najpierw 23 przypadki z trzech modułów:
`test_sqlite_snapshot.py`, `test_sqlite_recovery_rehearsal.py` oraz
`test_password_reset_http.py`. Błąd zatrzymuje bramę przed pełną regresją,
z podaniem publicznej nazwy pliku i numeru linii z JUnit. Po zaliczeniu
wykonuje się pełna izolowana regresja. Te 23 przypadki są podzbiorem pełnej
regresji i nie są liczone jako dodatkowe unikalne testy.

Pełna regresja zapisuje dodatkowo `failed_modules`: tylko nazwy istniejących
modułów w katalogu `tests`, bez surowych logów, `output_tail`, parametrów,
tokenów i ścieżek prywatnych. Osobne testy sprawdzają filtrowanie oraz
zatrzymanie przed pełnym przebiegiem po błędzie wstępnego testu.
Minimalną liczbę przypadków bramy Chromium zaktualizowano z 7 do 9.

Lokalnie: **49 PASS, 0 FAIL, 0 SKIP**, cztery moduły w izolowanych procesach.
Odcisk i oczyszczone wyniki: `audits/windows_recovery_local_2026-10-18.json`.
Pełna regresja Linux tego kodu: **3642 PASS, 0 FAIL, 19 SKIP**, wszystkie
290 modułów, osobne procesy i bazy w sześciu grupach. Źródła nie zmieniły się
podczas przebiegu; sprawdzono skróty wszystkich testów. Podsumowanie:
`audits/windows_recovery_linux_2026-10-18.json`.

Badany commit w CI: `a53db8983315685de5ac56e0447e06e7cf5fc5e1`.
Przebieg: https://github.com/Orgian1/WiejskaPaka/actions/runs/39097778222
PostgreSQL ponownie zaliczył 15/15, Chromium 9/9 i pięć viewportów HTTP.
Raporty w `audits/windows_recovery_ci_2026-10-18/` pobrano z artefaktów
i sprawdzono sumy SHA-256 archiwów.

Natywny Windows po zmianie zaliczył najpierw **23/23** przypadki odtwarzania,
a następnie pełną regresję: **3637 PASS, 0 FAIL, 24 SKIP** (3661 przypadków).
Wszystkie trzy bramy CI zakończyły się sukcesem. Odciski kodu, testów,
zależności i workflow są identyczne w trzech natywnych raportach i odpowiadają
bieżącym plikom projektu. To rzeczywiste wykonanie na runnerze Windows.

| Kontrola | PASS | FAIL | SKIP |
| --- | ---: | ---: | ---: |
| Pełna regresja Linux | 3642 | 0 | 19 |
| Pełna regresja Windows | 3637 | 0 | 24 |
| Wstępny test Windows (powtarzany podzbiór) | 23 | 0 | 0 |
| PostgreSQL | 15 | 0 | 0 |
| Chromium | 9 | 0 | 0 |

Liczba pominięć Windows nie wzrosła wobec wcześniejszego niezaliczonego
przebiegu (24). Trzy wcześniejsze błędy zniknęły; dodano trzy nowe przypadki
regresyjne. Wyników z różnych środowisk ani wstępnego podzbioru nie sumujemy
jako unikalnych przypadków. Pominięte testy nie są traktowane jako zaliczone.

Raport końcowy Windows: `audits/windows_recovery_ci_2026-10-18/windows.json`.
Archiwum artefaktu nr 12126091381 sprawdzono SHA-256:
`a37fb689b422db502c3c9b5f9495094bce1e2f127bfa01295f8adf57e8af2599`.
Pozostałe artefakty: PostgreSQL 12124694870, Chromium 12124569133.

Zapis niniejszych wyników z `[skip ci]` zmienia wyłącznie README i dokumentację
oraz oczyszczone podsumowania. Nie zmienia źródeł, testów, SQL, zależności ani
workflow badanego commitu. Nadal nie potwierdzono Windows ACL i nie włączono
resetu dla PostgreSQL, rzeczywistych płatności, wysyłki ani produkcyjnego hostingu.
Nie zmieniono danych użytkownika, `main`, produkcyjnej konfiguracji ani usług.

Źródło wymagania uchwytu z prawem zapisu:
https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-flushfilebuffers
