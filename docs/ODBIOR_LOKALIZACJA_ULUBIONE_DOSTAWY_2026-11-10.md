# Poprawki po ręcznym odbiorze — lokalizacja, ulubione i dostawy

PR #56, gałąź `preview/location-favorites-delivery-20261110`, baza #55.
Zachowano wcześniejszy kod, formularz kontaktowy i zmiany zwykłego czatu.
Nie zmieniano VPS ani jego danych, nie podłączano prawdziwych płatności i poczty.

## Lokalizacja klienta i ulubione

Obok „Blisko mnie” znajduje się zakładka „Ulubione”. Serduszka pod ofertami
katalogu i wyszukiwania w okolicy dodają i usuwają produkt z ulubionych.
Widok pobiera aktualną dostępność i cenę; niedostępny produkt można usunąć.
Lista nie jest kopią ceny ani gwarancją rezerwacji. Nadal obowiązują kontrole
stanu magazynu i kwot przy zakupie.

Wybrane miejsce, promień i maksymalnie 200 identyfikatorów ulubionych są
zapamiętywane lokalnie w tej przeglądarce, osobno według ID i e-maila konta.
Nie zapisujemy haseł, tokenów, PIN-ów ani treści adresu. Identyfikator konta
i współrzędne są ustawieniami lokalnymi; nie jest to synchronizacja między
urządzeniami. Przeglądarka z wyłączonym zapisem zachowa je tylko do wylogowania.
Wylogowanie czyści widok, a „Wyczyść lokalizację i wyniki” usuwa zapamiętane miejsce.

Po ponownym zalogowaniu kliknięcie „Blisko mnie” używa przywróconego miejsca
bez ponownego pobierania GPS. Wybór znalezionego adresu od razu uruchamia
wyszukiwanie produktów. Współrzędne są przekazywane w treści POST, nie w URL.
Odczyt ulubionych wymaga zalogowania i przyjmuje ograniczoną, zweryfikowaną
listę identyfikatorów; konto nie może uzyskać prywatnych danych innego konta.

## Lokalizacja punktu sprzedawcy

Adres punktu jest podawany jako miejscowość i ulica. Dostępne są przyciski
„Znajdź wpisany adres” oraz „Ustaw bieżącą lokalizację punktu”. Współrzędne
pozostały pod zamkniętą opcją zaawansowaną. Zmiana wpisanego adresu unieważnia
wcześniej wybraną lokalizację; stare odpowiedzi nie mogą zmienić innego punktu.
Lokalizacja punktu jest publiczna. Przed zapisaniem sprzedawca sprawdza miejsce.

GPS wymaga kliknięcia i zgody. Rozróżniane są: brak HTTPS/localhost, odmowa
zgody, przekroczony czas i brak pozycji z urządzenia. Po timeout lub braku
pozycji następuje jedna próba z większą dokładnością. Zmiana konta blokuje
ponowienia i spóźnione wyniki poprzedniego użytkownika.

**Ograniczenie demo:** bez skonfigurowanej usługi geokodowania wyszukiwanie
adresu obejmuje zapisane punkty. Nie rozpoznaje dowolnego nowego adresu w Polsce.
Nie podstawiamy fikcyjnych współrzędnych. Ustawienia systemowe Windows i zgody
Chrome muszą pozwalać na lokalizację; aplikacja nie może ich ominąć.
Test z wirtualną pozycją w Chromium nie potwierdza rzeczywistego sygnału GPS
na komputerze właściciela. Rozpoznawanie nowych adresów wymaga osobnego
podłączenia usługi mapowej opisanej w `WYSZUKIWANIE_ADRESU_2026-10-21.md`.

## Zamówienie i odbiór

W pełnym demo `WP_ENABLE_AUTOMATIC_PICKUP=1`. Udana płatność testowa za
zamówienie z odbiorem, po rezerwacji właściwego stanu magazynu, automatycznie
oznacza je jako gotowe do odbioru. Sprzedawca nie musi zatwierdzać zwykłego
zamówienia. Właściwy jednorazowy PIN nadal potwierdza wydanie; usunięto
checkboxy „klient sprawdził towar” z panelu sprzedawcy i dostawcy.
Starsze klienty API z polem checked_goods pozostają zgodne; nowy interfejs
przesyła sam PIN. Tryb bez flagi automatycznego odbioru zachowuje starszy
proces serwera. Flaga jest włączana jawnie przez launcher `--full-demo`.

Dostawa na adres nadal wymaga uzgodnienia. Sprzedawca może zaakceptować
pierwotny termin albo zaproponować inną datę oraz przedział godzin.
Nowy termin wymaga odpowiedzi klienta: „Przyjmuję nowy termin” lub
„Nie pasuje mi nowy termin”. Sprzedawca nie może sam przyjąć swojej propozycji.
Odrzucenie propozycji pozostawia pierwotną prośbę oczekującą; nie pobiera
płatności ani nie zwraca środków. Akceptacja aktualizuje całą przesyłkę.
Historia zachowuje propozycje, rewizje i zdarzenia, a powiadomienia wskazują
zmianę terminu. Propozycja nie przedłuża 30-minutowej rezerwacji.

## Migracja i wycofanie

Nowa opcjonalna migracja: `database/optional_delivery_proposals.sql`, po
`optional_address_delivery.sql`. Dodaje tabelę delivery_time_proposals bez
przepisywania starych zamówień. Manifest i blokada sum obejmują 41 plików SQL.
Preflight oraz start aktywnego modułu wymagają nowej tabeli. SQLite pełnego
demo tworzy ją w nowej jednorazowej bazie.

Na VPS najpierw wykonać kopię i próbę odtworzenia, a migrację sprawdzić na
odtworzonej kopii. Nie uruchamiać starego kodu z oczekującymi propozycjami:
nie pokazuje on klientowi ich stanu. Przed rollbackiem wstrzymać nowe zamówienia
i uzgodnić lub zamknąć oczekujące sprawy, zachowując tabelę i historię.
Nie odtwarzać sald ani danych z przeszłości automatycznie.

## Aktualizacja kopii Windows

Dotyczy odrębnego worktree `C:\Users\sylwi\Desktop\WiejskaPaka-DEMO-aktualne`
na commicie cbef660. Nie dotyczy oryginalnego katalogu ani VPS.
W oknie działającego demo nacisnąć Ctrl+C. Launcher usuwa jednorazową bazę;
próbne zamówienia i losowe konta z tego uruchomienia nie przechodzą do nowego.

W nowym oknie PowerShell uruchomić poniższy blok. Przy jakichkolwiek lokalnych
zmianach zatrzyma się przed zmianą wersji. Nie używać reset, clean ani pull
na odłączonym HEAD. Nie wysyłać zrzutów z hasłami i tokenami.

```powershell
& {
Set-Location -LiteralPath "$env:USERPROFILE\Desktop\WiejskaPaka-DEMO-aktualne" -ErrorAction Stop
$demoChanges = @(git status --porcelain)
if ($LASTEXITCODE -ne 0) { throw "To nie jest katalog repozytorium" }
if ($demoChanges.Count -gt 0) { throw "Są lokalne zmiany. Zachowaj je przed aktualizacją." }
git fetch origin preview/location-favorites-delivery-20261110
if ($LASTEXITCODE -ne 0) { throw "Pobieranie nie powiodło się" }
git switch --detach origin/preview/location-favorites-delivery-20261110
if ($LASTEXITCODE -ne 0) { throw "Nie zmieniono wersji" }
.\.venv\Scripts\python.exe scripts/run_phone_demo.py --full-demo
}
```

Otworzyć `http://127.0.0.1:8765`. Wykorzystać nowe konta pokazane przez launcher.
Dla GPS zezwolić na lokalizację w ustawieniach Windows i witryny Chrome.
Adres HTTP z lokalnym adresem IP na telefonie nie jest bezpiecznym kontekstem;
GPS telefonu wymaga HTTPS. Ręczny wybór zapisanego miejsca działa bez GPS.

## Weryfikacja

Kod badany: `56f06549d8d9e67f4fc8e18df453ad358343e709`,
drzewo `8afcb58a4ed2cb7dbc18ab2b71ee9e959accf208`.
Przebieg [Native test gates 42871199783](https://github.com/Orgian1/WiejskaPaka/actions/runs/42871199783).

| Sprawdzenie | Wynik |
|---|---|
| PostgreSQL 16, natywne API i restart | 99 PASS, 0 FAIL, 0 SKIP |
| PostgreSQL 17, natywne API i restart | 99 PASS, 0 FAIL, 0 SKIP |
| Szybki Windows: demo, odzyskiwanie i rozliczenia | 91 PASS, 0 FAIL, 0 SKIP |
| Chromium: zdjęcia i interfejs wszystkich ról | 84 PASS, 0 FAIL, 0 SKIP |
| Rzeczywisty HTTP, 5 szerokości ekranu | PASS |
| Pełna izolowana regresja Windows | 4941 przypadków: 4656 PASS, 0 FAIL, 285 SKIP |
| Lokalny zestaw celowany po ostatniej zmianie | 79 PASS, 0 FAIL, 0 SKIP |

Nowe scenariusze Chromium sprawdzają 320 i 1280 px: ulubione, geolokalizację
z wirtualną pozycją, wylogowanie i przywracanie ustawień konta, adres punktu
sprzedawcy oraz propozycję terminu i odpowiedź klienta. Kontrola HTTP obejmuje
pięć szerokości ekranu; nie jest to test fizycznego telefonu ani sygnału GPS.

Pełny lokalny przebieg Linux na wcześniejszym commicie `3636e653`:
390 modułów / 4941 przypadków: 4770 PASS, 69 FAIL, 102 SKIP. Wszystkie 69 błędów
pochodzi z uruchamiania Chromium blokowanego przez środowisko
(`AF_UNIX Operation not permitted`). Nie przedstawiamy go jako pełnego sukcesu.
Po tym przebiegu zmieniono wyłącznie oczekiwaną listę nawigacji w narzędziu
`check_mobile_offline.py` (dodano Ulubione); końcowe CI obejmuje tę zmianę.
Osobny wcześniejszy zestaw celowany miał 115 PASS. Liczb tych nie sumujemy,
ponieważ zestawy pokrywają się. Końcowa dokumentacja nie zmienia badanego kodu.

W `audits/market_review_2026-11-10/` zapisano oczyszczone raporty i sumy
źródeł, zależności oraz workflow. Sumy ZIP pobranych artefaktów porównano
z metadanymi GitHub, a każdy wynik z dokładnym odciskiem źródeł commita.
Raporty nie zawierają surowych logów ani danych logowania.

Wszystkie pięć zadań GitHub Actions zakończyło się sukcesem. W pełnym zestawie
Windows 285 przypadków pominięto; nie traktujemy ich jako zaliczonych.
Osobne bramy PostgreSQL i Chromium wykonały opisane wyżej testy bez pominięć.
Wersja lokalnego demo nadaje się do ponownego ręcznego odbioru. VPS pozostaje osobnym etapem: brak sprawdzonego dostępu,
aktualnego odczytu usług i próby odtworzenia jego kopii. Procedura:
`WDROZENIE_I_WYCOFANIE_DEMO_2026-11-10.md`. Dowolne nowe adresy wymagają
konfiguracji geokodera. Żaden test nie potwierdza fizycznego GPS Windows właściciela.
