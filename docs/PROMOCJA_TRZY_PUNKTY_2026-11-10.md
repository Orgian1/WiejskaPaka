# Kod WIEJSKAPAKA — trzy bezpłatne punkty odbioru

PR #57, gałąź `preview/pickup-promo-december-20261110`, baza PR #56.

W panelu sprzedawcy, nad formularzem nowego punktu odbioru, jest pole „Kod
promocyjny”. Wpisanie `WIEJSKAPAKA` (także `wiejska paka`, bez rozróżniania
wielkości liter) aktywuje na koncie promocję do końca **31 grudnia 2026 r.**
według czasu w Polsce. Nie jest to miesiąc liczony od wpisania kodu.
Granica wyłączna: 1 stycznia 2027, 00:00 Europe/Warsaw.

Promocja obejmuje pierwsze trzy aktywne punkty sprzedawcy w kolejności dodania.
Jeśli punktów jeszcze nie ma, trzy miejsca czekają na ich utworzenie.
Nowe punkty zajmują wolne miejsca; czwarty jest poza promocją. Nieaktywne punkty
nie zajmują miejsca. Lista punktów objętych promocją jest widoczna w panelu.
Trzy oznacza różne miejsca odbioru, nie trzy dni obecności i nie trzy punkty
przy każdym ponownym wpisaniu kodu. Nie dodajemy osobnego modelu tras.

Kod zapisuje uprawnienie na koncie po stronie serwera. Przetrwa odświeżenie,
wylogowanie, inne urządzenie i restart serwera z tą samą bazą. Nie dotyczy
jednorazowej bazy lokalnego launchera: jej usunięcie usuwa również próbne konta.
Ponowienie jest bezpieczne, również równoległe: jeden wpis na konto i kampanię,
bez mnożenia limitu ani przedłużania terminu. Klient nie podaje daty ani limitu.
Uprawnienie wymaga roli sprzedawcy i ponownej kontroli sesji w transakcji.

**Granica wersji demo:** obecny moduł punktów nie ma płatnego cennika i nie
pobiera opłat także bez kodu. Promocja zapisuje i pokazuje konkretne uprawnienie
do trzech punktów; nie dodaje nieuzgodnionych opłat za pozostałe miejsca.
Nie zmienia salda, prowizji 5% od wypłat sprzedawcy ani kosztu dostawy.
Po wygaśnięciu nie uruchamia płatności, nie wyłącza punktów i nie anuluje
istniejących zamówień. Rozliczenie płatnych punktów po promocji będzie osobnym
etapem po ustaleniu cennika i podłączeniu płatności.

## Uruchomienie i zgodność

`run_phone_demo.py --full-demo` włącza `WP_ENABLE_PICKUP_PROMOTION=1` i tworzy
tabelę na jednorazowej SQLite. Na trwałym podglądzie flaga domyślnie wyłączona.
Włączenie wymaga nowej opcjonalnej migracji `database/optional_pickup_promotion.sql`.
Manifest zawiera 42 migracje, poprzednie 41 plików i ich sumy pozostają bez zmian.
Preflight i lifespan sprawdzają obecność tabeli po włączeniu funkcji.

VPS nie był zmieniany. Najpierw aktualny odczyt stanu, spójna kopia i próba
odtworzenia zgodnie z `WDROZENIE_I_WYCOFANIE_DEMO_2026-11-10.md`, następnie
migracja na odtworzonej kopii. Przy wycofaniu zachować tabelę uprawnień;
wcześniejszy kod ją ignoruje. Nie odtwarzać starej bazy nad nowszymi zamówieniami.
Koniec promocji jest sprawdzany przez serwer przy każdym odczycie i aktywacji;
nie wymaga zadania pobierającego opłaty ani automatycznego kasowania punktów.

Aby zobaczyć funkcję w kopii Windows, trzeba zatrzymać jednorazowe demo (utrata
jego próbnych kont), sprawdzić `git status --short`, pobrać gałąź #57 i przejść
na nią przez `git switch --detach origin/preview/pickup-promo-december-20261110`,
a następnie uruchomić dotychczasowy launcher `--full-demo`. Nie używać `pull`
na odłączonym HEAD ani nadpisywać lokalnych zmian.

### PowerShell — oddzielna kopia demo Windows

Najpierw Ctrl+C w oknie działającego jednorazowego demo. Jego próbne dane zostaną
usunięte. Poniższy blok zatrzyma się przy lokalnych zmianach albo błędzie Git:

```powershell
& {
Set-Location -LiteralPath "$env:USERPROFILE\Desktop\WiejskaPaka-DEMO-aktualne" -ErrorAction Stop
$demoChanges = @(git status --porcelain)
if ($LASTEXITCODE -ne 0) { throw "To nie jest katalog repozytorium" }
if ($demoChanges.Count -gt 0) { throw "Są lokalne zmiany. Zachowaj je przed aktualizacją." }
git fetch origin preview/pickup-promo-december-20261110
if ($LASTEXITCODE -ne 0) { throw "Pobieranie nie powiodło się" }
git switch --detach origin/preview/pickup-promo-december-20261110
if ($LASTEXITCODE -ne 0) { throw "Nie zmieniono wersji" }
.\.venv\Scripts\python.exe scripts/run_phone_demo.py --full-demo
}
```

Otworzyć `http://127.0.0.1:8765`, zalogować się nowym kontem sprzedawcy
pokazanym przez launcher i znaleźć pole kodu nad nowym punktem odbioru.
Nie publikować zrzutów z hasłami, tokenami ani PIN-ami.

## Testy

Weryfikowany commit kodu: `7e76265ba3f54a7d6c4983ffde998826be292f33`.
[Przebieg GitHub Actions](https://github.com/Orgian1/WiejskaPaka/actions/runs/42883413588).

Lokalnie dwa izolowane zestawy: 37 PASS i 76 PASS, bez błędów i pominięć.
Sprawdzono granicę północy w Polsce, ponawianie, sześć równoległych aktywacji,
limit i kolejność punktów, inne konta, rolę klienta, nieprawidłowy kod,
niezaufaną datę/limit w payloadzie i cofniętą sesję mimo starego wyniku zależności.
Test Node sprawdza, że stare odpowiedzi odczytu i zapisu po wylogowaniu nie
odtwarzają danych poprzedniego sprzedawcy ani nie czyszczą nowego formularza.

Dodano natywny PostgreSQL z restartem i porównaniem niezmienionego portfela
oraz rzeczywistą przeglądarkę przy 320/1280 px: błędny kod, poprawna aktywacja,
trzy z czterech punktów, ponowne logowanie i czyszczenie przy wylogowaniu.
Aktywny scenariusz przeglądarki po zakończeniu kampanii będzie jawnie pomijany;
granica wygaśnięcia jest niezależnie testowana zegarem modułu API.

| Brama | Wynik |
|---|---|
| PostgreSQL 16 | 100 PASS, 0 FAIL, 0 SKIP |
| PostgreSQL 17 | 100 PASS, 0 FAIL, 0 SKIP |
| Szybki Windows | 91 PASS, 0 FAIL, 0 SKIP |
| Chromium, zdjęcia i panele ról | 86 PASS, 0 FAIL, 0 SKIP |
| Rzeczywisty HTTP, pięć szerokości | PASS |
| Pełny Windows | 4954 przypadków: 4666 PASS, 0 FAIL, 288 SKIP |
Dowody w `audits/pickup_promotion_2026-11-10/`. Historyczne raporty #56
pozostają raportami poprzedniego commita i nie są przedstawiane jako dowód #57.

Pierwszy pełny Windows zgłosił jeden błąd w starej liście zasobów HTML:
brak nowego pickup-promotion.js w oczekiwaniu testu. Uzupełniono wyłącznie tę
listę; kod aplikacji pozostał identyczny. Lokalna regresja po korekcie: 26 PASS.
Diagnostyka pierwszego przebiegu jest w podkatalogu first-run.

Końcowy przebieg: wszystkie pięć zadań GitHub Actions zakończone sukcesem.
Pominiętych przypadków Windows nie liczymy jako zaliczonych. Osobne bramy
PostgreSQL i Chromium wykonały wskazane testy bez pominięć. Końcowy zapis
dokumentacji zachowuje identyczny kod, testy, zależności i workflow.
