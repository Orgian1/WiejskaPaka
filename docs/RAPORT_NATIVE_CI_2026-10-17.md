# WiejskaPaka — rzeczywiste testy natywne, 17.10.2026

Badany commit gałęzi `wiejskapaka-import`:
`52763d75b003d13a78e016ef4ac9dac333dabaea`.
Przebieg GitHub Actions:
https://github.com/Orgian1/WiejskaPaka/actions/runs/39048530999

## Potwierdzone wyniki

| Środowisko | PASS | FAIL | SKIP | Zakres |
| --- | ---: | ---: | ---: | --- |
| Linux, Python 3.12.14, Node 24.19.0 | 3596 | 0 | 17 | Pełna lokalna regresja, 284/284 moduły, 3613 przypadków |
| Windows w Actions | 3592 | 0 | 21 | Pełna izolowana regresja, 3613 przypadków |
| PostgreSQL 16 w Actions | 15 | 0 | 0 | Rzeczywisty silnik, migracje, transakcje, ograniczona rola i HTTP |
| Chromium w Actions | 7 | 0 | 0 | Offline i cztery role |

Osobna kontrola Chromium przez rzeczywiste HTTP przy pięciu rozmiarach okna
również zakończyła się sukcesem. Nie jest doliczana do przypadków pytest.
Wszystkie trzy zadania oraz cały przebieg Actions zakończyły się `success`.
Windows potwierdził kompletność i brak zmian źródeł; brama wymaga wykonania
całego planu 284 modułów. Był to rzeczywisty runner Windows, nie emulacja.

Regresja Linuksa została wykonana od początku, bez wznowienia i bez zmian źródeł
podczas testów. `complete`, `success` i `sources_unchanged` mają wartość `true`.
Przyrost o 23 przypadki względem raportu v9 to nowe próby sterownika CI.
Są to testy z makietami procesów; dowodem natywnego PostgreSQL i Chromium
są osobne zakończone zadania Actions, a nie makiety.

17 pominięć Linuksa obejmuje 15 przypadków PostgreSQL i dwa przypadki
przeglądarkowe. Ich rzeczywiste odpowiedniki zaliczono w osobnych bramach.
Windows ma dodatkowo cztery pominięcia kontroli wymagających POSIX
(uprawnienia mode bits i rotacja z directory fsync). Windows ACL oraz rotacja
kluczy na Windows nie są przez to potwierdzone; rotacja pozostaje tam
blokowana zgodnie z istniejącą ochroną. Nie osłabiano tego ograniczenia.
Wyniki częściowo się pokrywają: nie należy sumować tabeli jako liczby unikalnych
testów ani zamieniać historycznych SKIP na PASS w raporcie Linuksa.

## Integralność dowodów

Zachowano oczyszczone JSON-y w
[`audits/native_ci_2026-10-17`](audits/native_ci_2026-10-17).
Nie zawierają surowych logów, zmiennych środowiska, baz, kluczy, PIN-ów
ani danych osób. Archiwa Actions pobrano i sprawdzono względem SHA-256
podanego przez API GitHub. Odciski źródeł we wszystkich trzech natywnych raportach zgadzają
się z badanym commitem i lokalnym drzewem źródeł:

| Zakres | SHA-256 |
| --- | --- |
| Kod wykonywalny | `0047ac6619a8ef0c750403575f71a90056fda7a8ea59fe296645aff09f0464e0` |
| Manifest modułów testowych | `6a7b4f81e8d79de61b34726a54cc9938603fae010cc7d3c82ff47584c4b4a5ee` |
| Wszystkie źródła testów i helperów | `f1a6462fabc527e90df0ea512094027509e3f684ea0f21a6ae62ba2dd0f77f2c` |
| Deklaracje zależności | `f7022625641feafbd1ec67d953fc74e11d373307d584eead2cb23cbd4068bd62` |
| Workflow | `2bca985608643a19f0f68865cfc5a1f79858a1687c4510944d158a4445a4561a` |

Regresja lokalna używa starszego odcisku, obejmującego kod i deklaracje
zależności: `b81b482fe0a61f6a035994f86dcef1f57147a973aa40e5dfd9338916d6925d5c`.
Nie należy porównywać go bezpośrednio z odciskiem samego kodu powyżej.

| Artefakt Actions | ID | SHA-256 archiwum ZIP |
| --- | --- | --- |
| postgres-summary | 12106707148 | `fb37bc82cd30ae84a16fa84f3b80c33470ceb243645a07f294dfc067d7870619` |
| windows-summary | 12106619858 | `0f6bd3a705ec37fa8027312a2ec19a8ea8a6643846bc43d88a993270406633ec` |
| chromium-summary | 12106548640 | `6a9b836e30959e0c62632332a690758767a5a6df14f0716b3f795198a0747f05` |

## Co zmienił GitHub

Pakiety v1–v9 zostały zsynchronizowane na gałęzi roboczej. Dodano przypięty
do SHA workflow i sterownik izolowanych bram, bez dostępu do produkcyjnych
baz i sekretów. PostgreSQL korzysta z jednorazowego lokalnego kontenera
z syntetycznymi danymi. Testy płatności pozostają symulacjami.
Szczegóły: [`NATYWNE_TESTY_CI.md`](NATYWNE_TESTY_CI.md).

Dokumentację i oczyszczone dowody opublikowano osobnym commitem
z `[skip ci]`: zmienia on tylko README i pliki w `docs/`. Nie zmienia kodu,
testów, zależności ani workflow, których odciski pozostają identyczne.
Wyniki powyżej dotyczą wskazanego badanego commitu, a nie nowego przebiegu
po zmianie samej dokumentacji.

## Nierozwiązane kwestie i gotowość

19 historycznych lokalnych modułów nie ma w repozytorium. Nie odtworzono
więc dokładnie pierwotnego zestawu 3591 przypadków użytkownika i nie można
przypisać wszystkich dawnych 37 błędów do konkretnych obecnych poprawek.
Poprzednie raporty rozróżniają odtworzone usterki, różnice środowiska
i nowe syntetyczne przypadki bezpieczeństwa.

Nadal potrzebne są pełny audyt bezpieczeństwa i RLS, weryfikacja praw
konsumentów, wydajności, kopii zapasowych i odtwarzania. Natywne testy nie
zastępują tych prac ani weryfikacji rzeczywistego operatora płatności.
**Aplikacja pozostaje wersją testową i nie jest gotowa do wdrożenia produkcyjnego.**

Nie zmieniono `main`, nie wykonano force push ani wdrożenia. Nie podłączano
domeny, hostingu i rzeczywistych płatności. Zachowano grosze jako liczby
całkowite, pojedynczą opłatę za przesyłkę, PIN, pełny zwrot przy winie
dostawcy oraz ochronę numerów telefonów. Nie usuwano danych ani kluczy
użytkownika i nie podłączano jego istniejących baz.
