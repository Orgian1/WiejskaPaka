# WiejskaPaka — końcowe przygotowanie demo, 13.11.2026

Repozytorium: `Orgian1/WiejskaPaka`.
Gałąź: `codex/demo-finalization-fixes-20261112`.
Baza: `1feaff462fddb2c9b2f3acc02163b34789c72371`, zgodna z GitHubem przed zmianami.
Przejrzano historię GitHub, raporty i kod; zachowano wcześniejsze funkcje.
Kod aplikacji zapisano jako `d5297fd9d16d97940a4cf111e3cb000fac0b1452`.
SHA końcowego commita z raportem podano w odpowiedzi po push; dowody zawierają
hashe źródeł i testów.

## Co zmieniono

- Naprawiono stan wyszukiwarki mapy: po błędzie nie pozostaje „Szukam adresu”.
  Trwały, dostępny komunikat rozróżnia brak internetu, niedostępność usługi,
  limit zapytań i przekroczenie czasu 8 sekund. Ponowne wyszukiwanie, ręczny
  wybór miejsca i GPS pozostają dostępne; opóźnione odpowiedzi nie zmieniają
  nowej sesji ani nowego adresu.
- Zachowano Photon dla Polski z jawnym `--public-geocoder photon`: miejscowość,
  ulica i numer w polu ulicy, do pięciu wyników, ustawienie znacznika po wyborze.
  Wynik zależy od pokrycia danych usługi. Nie dodano opłat, kluczy API ani
  automatycznej wysyłki zapytań bez kliknięcia.
- Zachowano zapis kolejności na koncie sprzedawcy, ochronę wersji, zgodność
  dwóch urządzeń i podział dłuższej trasy na części. Dodano test rzeczywistego
  interfejsu z dziewięcioma punktami: żaden przystanek nie ginie, części łączą
  się z poprzednim końcem i nie przekraczają trzech waypointów.
- Uzupełniono panel dostawcy o trasę aktywnych dostaw. Adresy są pobierane na
  żądanie z istniejącego endpointu autoryzującego przydział. Wspólny adres
  produktów jednej przesyłki daje jeden przystanek. Przed przygotowaniem linku
  ponownie sprawdzane są aktywne adresy; zakończona dostawa usuwa się z listy.
  Link otwiera Mapy Google po osobnym kliknięciu, bez telefonu i tokenów.
  To uporządkowana lista aktywnych adresów, bez optymalizacji i bez ETA.
- Launcher ma opcjonalny `--host` prywatnego IPv4 LAN z wymaganym certyfikatem
  i kluczem HTTPS. Domyślnie pozostaje loopback. Odrzuca publiczne IP,
  `0.0.0.0`, niekompletne i niepasujące pliki TLS. Działa wyłącznie na
  jednorazowej bazie demo, bez dziedziczenia usług produkcyjnych.
- Uzupełniono instrukcję prawdziwego telefonu (Wi-Fi, lokalny CA, HTTPS, GPS),
  zachowując instrukcję desktopu, oraz procedurę aktualizacji VPS z backupem,
  migracją na kopii, odrębnym podglądem i wycofaniem. Niczego nie wdrożono.

## Zakres kontroli paneli

| Panel | Kontrola |
| --- | --- |
| Klient | Katalog i szczegóły pod rzędem, ulubione per konto, zapamiętana lokalizacja/GPS, koszyk, zamówienia i przesyłki, PIN, portfel testowy |
| Sprzedawca | Produkty i magazyn, mapa punktów, kolejność na koncie, grupy zamówień, dostawy/propozycje terminu, promocje, rozliczenia i wypłaty testowe |
| Dostawca | Własne przydziały, aktywne adresy i trasa, status, PIN przesyłki i odebranie dostępu do zakończonych dostaw |
| Administrator | Autoryzacja konta, przegląd profili sprzedawców, konfiguracja kodów promocyjnych, zgłoszenia, rejestr/audyt przesyłek i raporty/CSV |

Bezpieczeństwo i rozliczenia: separacja danych kont, sesje i reset haseł,
nieujawnianie telefonów, dostęp do adresów według przydziału, kwoty w groszach,
prowizje 5%/0%, jedna opłata dostawy, pełne zwroty, blokady podwójnego
księgowania, jednorazowy PIN i współbieżność w SQLite/PostgreSQL.
Nie zmieniano tych zasad biznesowych.

## Końcowe wyniki

| Zestaw | PASS | FAIL | SKIP |
| --- | ---: | ---: | ---: |
| Pełna regresja izolowana, 401 modułów | 4925 | 0 | 106 |
| Pełna natywna bramka PostgreSQL 17.11 | 103 | 0 | 0 |
| Rozszerzony zestaw przeglądarkowy | 115 | 0 | 0 |
| Osobna kontrola zdjęć w Chromium | 2 | 0 | 0 |

Kontrola HTTP/Chromium przy szerokościach **320, 360, 390, 768 i 1280 px**
zakończyła się sukcesem. Obie natywne bramki mają `success=true` oraz
`sources_unchanged=true`; ich hashe odpowiadają finalnemu kodowi.

106 pominięć pełnej regresji: 103 przypadki PostgreSQL uruchomione osobno,
jeden rozszerzony test ról zaliczony osobno w bramce przeglądarkowej oraz dwa testy zachowania na
platformie innej niż POSIX, niewykonane na Linuksie. Wszystkie 401 modułów
ukończono; źródła i testy zweryfikowano hashami. Kontrola sum 44 migracji,
składni zmienionego JS i `git diff --check` przeszła. Nie zmieniano SQL.

Pierwszy połączony przebieg przeglądarkowy podczas równoległej pełnej regresji
osiągnął limit 600 sekund i jest zapisany jako **niekompletny TIMEOUT**.
Powtórkę wykonano z całym tym samym zestawem i limitem 1200 sekund, po zakończeniu
pozostałych zestawów. Nie usuwano przypadków ani asercji. Pierwszego przebiegu
nie zaliczono do wyników końcowych.

Bramka z większym budżetem używa tej samej funkcji `scripts.run_native_ci.run`
i pełnej listy `BROWSER_TESTS`. Odtworzenie z katalogu repozytorium:

```python
import subprocess
from pathlib import Path
from scripts.run_native_ci import run

def runner(command, **kwargs):
    if 'pytest' in command and '-v' in command and len(command) > 10:
        kwargs['timeout'] = 1200
    return subprocess.run(command, **kwargs)

result = run('browser', Path('/tmp/wiejskapaka-browser.json'), runner=runner)
raise SystemExit(0 if result['success'] else 1)
```

Zapisz ten kod w nowym pliku pomocniczym i uruchom z Pythonem środowiska projektu
(przy pliku poza repo ustaw `PYTHONPATH` na katalog repozytorium). Na Windows
wybierz własną ścieżkę raportu zamiast `/tmp`.

Dowody: `docs/audits/final_demo_20261113/`. Zapisano wyniki i hashe,
bez surowych logów, haseł i danych kont. Powtarzających się przypadków między
zestawami nie dodaje się jako liczby unikalnych testów. Przerwane przebiegi
robocze nie są dowodem końcowej walidacji.

## Pozostające ograniczenia

1. Proxy tego środowiska blokuje publiczny Photon (`403` przy połączeniu).
   Rzeczywiste demo z Photon zwraca kontrolowane `503`; potwierdzono po nim
   działanie lokalnej mapy i GPS w Chromium. Poprawne polskie odpowiedzi i
   wybór adresu testowano kontrolowanym transportem. Nie potwierdzono dodatniego
   wyniku publicznego geokodowania z tej maszyny. Kafelki ulic OSM też wymagają
   dostępu sieciowego; lokalna mapa poglądowa nie pokazuje ulic.
2. Fizyczny telefon i Windows wymagają ręcznego odbioru właściciela.
   Wykonano emulację mobilnego ekranu/dotyku/GPS, kontrolę tabletu i desktopu
   oraz rzeczywiste HTTPS z weryfikacją certyfikatu na loopback. Instalacja
   mkcert/CA i połączenie prywatnej sieci Wi-Fi należą do odbioru na urządzeniach.
3. Ogólny edytor wszystkich kont i ustawień infrastruktury nie jest częścią
   panelu admina. Dostępne ustawienia obejmują promocje, a kontrola kont dotyczy
   autoryzacji i przeglądu sprzedawców. Konfiguracja usług zewnętrznych pozostaje
   po stronie operatora, poza panelem. Nie dodawano nieuzgodnionych reguł zmian ról.
4. Launcher tworzy jednorazowe konta/bazę; oba urządzenia muszą korzystać z tej
   samej działającej instancji. Restart launchera rozpoczyna nowe demo.
   Nie migrowano lokalnego zapisu kolejności ze starych przeglądarek.

## Odbiór

Demo jest przygotowane do ręcznych testów właściciela w zakresie opisanym wyżej.
Instrukcje:

- [Komputer, telefon i lista czynności](ODBIOR_WLASCICIELA_2026-11-13.md).
- [Plan aktualizacji VPS, kopia i rollback](AKTUALIZACJA_VPS_ODBIOR_2026-11-13.md).

Nie zmieniano main, działającego VPS, produkcyjnych danych ani PayU.
Nie publikowano środowiska. Stan istniejącej bazy VPS nadal wymaga kontroli
operatora przed ewentualnym osobno autoryzowanym wdrożeniem.
