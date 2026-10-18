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
Natywny Windows po zmianie wymaga nowego zakończonego przebiegu CI.
Nie zmieniono danych użytkownika, `main`, produkcyjnej konfiguracji ani usług.

Źródło wymagania uchwytu z prawem zapisu:
https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-flushfilebuffers
