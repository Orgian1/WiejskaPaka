# Paczka #60 — raport

Repozytorium: `Orgian1/WiejskaPaka`.
Gałąź: `codex/issue-60-separate-views-20261113`.
Baza: `codex/issue-59-pre-vps-20261113`,
`35c4c0aa0c48860e4ee1b19956acb629aab47c7c`.
Zgłoszenie: https://github.com/Orgian1/WiejskaPaka/issues/60.
Commit kodu poddany końcowym testom:
`b9e902ca09398848c20e3c166558653a87df0825`.
Późniejszy commit zawiera wyłącznie dokumentację i dowody.

## Zmiany

- Oddzielne widoki produktów, okolicy, ulubionych, koszyka, zamówień, portfela,
  konta, ogłoszeń, punktów, powiadomień, kontaktu i administracji. Hash URL
  obsługuje historię przeglądarki i odświeżanie bez konfiguracji rewrite serwera.
  Nie przenosi prywatnych danych ani tokenów do adresu. Prywatny URL po
  odświeżeniu pokazuje logowanie i otwiera żądany widok po poprawnej autoryzacji.
- Nawigacja jest dostępna klawiaturą, ma oznaczenie bieżącej strony i fokus
  nagłówka. Wylogowanie pozostaje dostępne z każdego widoku. Moduły tworzone
  po opóźnionym odczycie konfiguracji także przestrzegają aktywnego widoku.
  Zachowano bezpieczne przechwytywanie fragmentów resetu i weryfikacji e-maila.
- Katalog ma maksymalnie 20 ofert na stronie i numerowane przyciski z bieżącą
  stroną. Filtry, sortowanie i sprzedawca są zachowywane w publicznych parametrach
  trasy. Lokalizacja pozostaje w pamięci lub na koncie za osobną zgodą,
  bez współrzędnych w URL/storage. Zachowano rzędy, szczegóły pod rzędem i serca.
- „Moje ogłoszenia”: obraz, jednostka, cena, wolny stan i status, szybka edycja
  ceny/stanu, edytor opisu/kategorii i odsyłacz do panelu zdjęć. Usunięto widoczną
  duplikację starej listy magazynu. Konflikt `expected_stock` zapobiega
  nadpisaniu zapasu zmienionego w czasie edycji przez zakup. Istniejące zamówienia
  zachowują cenę i jednostkę. Nie zmieniano mechanizmu rezerwacji ani prowizji.
- Oferta ma odwracalny znacznik dostępności. Wycofana oferta znika z katalogu
  i wyszukiwania w okolicy oraz nie może być kupiona bezpośrednio ani przez koszyk.
  Zdjęcia, produkty, stany i zamówienia pozostają. Anulowanie wcześniejszego
  zamówienia przywraca wolny towar, ale nie wznawia automatycznie wycofanej oferty.
- Punkty odbioru mają własną zakładkę: dodawanie, pełna dotychczasowa edycja,
  daty, godziny, aktywność, promocje/opłaty i nawigacja. Pola współrzędnych
  w edycji są ukryte; wybór adresu, mapy lub GPS zapisuje je w tle.
  Ręczna mapa i wybór środka pozostają dostępne bez Photon.
- Usunięcie punktu wymaga jawnego potwierdzenia i autoryzacji właściciela.
  Aktywne zamówienia blokują usunięcie i zmianę miejsca/terminów. Wyłączenie
  nowych zakupów nadal jest możliwe. Usunięcie z aktywnych jest miękkie,
  zachowuje historyczne powiązania, PIN-y i wykorzystanie promocji.
- Kontakt jest jednym osobnym widokiem ze zwiniętym formularzem. Zgłoszenie
  problemu przy zakupie przenosi do niego i otwiera właściwy formularz.
  Liczniki #59 oraz uprawnienia wszystkich czterech ról pozostają.

## Baza i zgodność

Nowa migracja `optional_product_listing_states.sql` tworzy jedną tabelę
z kluczem obcym produktu i flagą active. Nie zmienia istniejących rekordów;
brak flagi oznacza dotychczasową aktywną ofertę. Manifest/preflight oraz przykład
psql uwzględniają **46 plików SQL**. Sumy poprzednich 45 pozostają takie same.
Sprawdzono powtórzenie migracji i zachowanie produktów. Brak nowych zależności.

## Testy

Końcowe wyniki i sumy źródeł: `audits/issue60_20261113/`.
Wyniki będą uzupełnione po zakończeniu pełnego przebiegu. Przed przerwaniem
środowiska potwierdzono 4987 PASS / 0 FAIL / 110 SKIP w 410 modułach oraz
107 PASS / 0 FAIL / 0 SKIP PostgreSQL. Końcowego raportu rozszerzonego Chromium
nie odebrano. Po odtworzeniu środowiska pliki `/tmp` były niedostępne,
dlatego ponawiany jest pełny przebieg, z raportami w trwałym `/workspace`.
Ten zapis jest szkicem raportu, a nie potwierdzeniem zakończenia nowej bramki.

Dotychczasowe testy UI przechodzą teraz między widokami przez rzeczywistą
nawigację. Nie wyłączano testów ani asercji finansowych i prywatności.
Oczekiwania na stary układ kilku jednocześnie otwartych sekcji zastąpiono
sprawdzeniem oddzielnych widoków. Testowe bazy minimalne uwzględniają nową tabelę.
Bramka rozszerzona Chromium ma 1800 sekund zamiast 600 dla powiększonego zestawu;
zestaw i warunki PASS pozostają kompletne. Dla lokalnego PostgreSQL przy
równoległej regresji zastosowano wrapper z budżetem 1200 sekund zamiast 600,
bez zmiany polecenia pytest, zestawu ani asercji. Wcześniejszy przebieg z
krótszym budżetem zakończył się timeoutem i nie jest zaliczany do wyników
końcowych. Wyniki wykonane przed ostatnimi poprawkami UI również zastąpiono
pełnym przebiegiem na zamrożonych źródłach.

## Odbiór i ograniczenia

[Jedno polecenie PowerShell, testy ręczne i plan VPS](ISSUE_60_DEMO_I_VPS_2026-11-13.md).
[Przygotowana treść PR](PR_ISSUE_60.md).

Testy wykonywane są na Linux/Chromium i jednorazowych lokalnych bazach.
Rozmiary telefonu/tabletu oraz kontrolowane uprawnienia GPS nie zastępują
fizycznego telefonu ani systemu Windows. Ten odbiór pozostaje do wykonania
przez właściciela. GPS na telefonie wymaga zaufanego HTTPS.

Publiczny Photon jest blokowany przez proxy tej chmury; adapter, błędy i wybór
mapy są testowane lokalnie. Do diagnozy w docelowej sieci służy
`python -m scripts.check_photon_demo`. Nie obchodzono TLS ani polityki sieciowej.
Ogólny kontakt e-mail pozostaje jawnie wyłączony bez usługi pocztowej;
zgłoszenia zakupowe zapisują się w bazie niezależnie od SMTP.

Nie zmieniano VPS, main, produkcyjnych danych ani rzeczywistych płatności.
Żadnego wdrożenia nie wykonano.

## GitHub i PR

Gałąź kodu została wypchnięta na origin. Próba `gh pr create` z właściwą bazą,
nową gałęzią, konkretnym tytułem i treścią zakończyła się
`Post https://api.github.com/graphql: Forbidden`.
**PR nie został utworzony**; nie obchodzono proxy ani nie proszono o tokeny.

[Ręczne utworzenie PR z właściwą bazą](https://github.com/Orgian1/WiejskaPaka/compare/codex/issue-59-pre-vps-20261113...codex/issue-60-separate-views-20261113?expand=1).
Treść znajduje się w `PR_ISSUE_60.md`. Samo push działa prawidłowo;
utworzenie PR przez API wymaga jego dostępności i odpowiednich uprawnień.
