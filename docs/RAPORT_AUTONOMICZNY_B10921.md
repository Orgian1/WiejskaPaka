# WiejskaPaka — raport autonomicznej pracy B/10921–B/11280

Data: 15 października 2026. Kod bazowy: załączone archiwum kontynuacji.
Sprawdzony commit kodu: `5ab90a7b3e1d5e192c91df585663ad938e1ff4ec`.
Odcisk źródeł aplikacji: `b5bc1cc7d3a27091dae191e190f90c9723d26902640587af7e98b202308ded38`.

## Wynik

Poprawiono bezpieczeństwo sesji i walidacji, reguły dostawy, zwroty oraz raporty.
**To wydanie testowe. Nie potwierdzono gotowości produkcyjnej ani wcześniejszego
szacunku 90% ukończenia. Nie oznacza to odhaczenia 360 numerowanych pozycji.**

| Weryfikacja | Rzeczywisty wynik |
|---|---|
| Pełna regresja, osobne procesy i bazy | 234 moduły; 2916 PASS, 0 FAIL, 12 SKIP |
| Natywny PostgreSQL | NIEZALICZONY; 10 pominiętych przypadków pytest |
| Rzeczywiste Chromium | NIEZALICZONE; ograniczenia środowiska |
| Stabilność rzeczywistego HTTP | 1200.3 s; 11142 rund; 85997 żądań; 203634 kontroli |
| Anonimowy dostęp HTTP | 79 z 79 prywatnych tras odrzuciło dostęp |
| Dostęp między kontami | 52 kontrole PASS |
| Nagłówki HTTP | 13 kontroli PASS |
| Unieważnianie sesji | 41 kontroli PASS |
| Blokada logowania | 13 kontroli PASS |
| Arytmetyka finansowa | 20 001 kwot; 100 002 kontrole PASS |
| Zależności | 31 pakietów sprawdzonych przez pip-audit; brak zgłoszonych znanych podatności; bez pominiętych pakietów |
| Składnia | compileall Python oraz node --check dla obu plików web: PASS |

Liczby żądań i kontroli w teście stabilności obejmują powtarzane scenariusze.
**Nie dodajemy ich do liczby odrębnych testów pytest.** SKIP nie jest PASS.
Raport regresji pochodzi z JUnit; potwierdza brak zmian źródeł podczas przebiegu.
W końcowym przebiegu użyto zwykłych asercji Pythona, aby wyeliminować problem
starej pamięci przepisanych testów w tym środowisku. Asercje były włączone.

## Wykryte problemy i poprawki

1. **Daty sesji porównywano jako tekst.** Wygasły token z innym offsetem mógł
   zostać przyjęty, a ważny odrzucony. Daty są parsowane jako chwile UTC;
   brak strefy i nieprawidłowa data powodują odmowę dostępu.
2. **Logowanie przyjmowało nieograniczone dane i nie resetowało okna po blokadzie.**
   Ograniczono długości, poprawiono reset licznika, dodano weryfikację zastępczego
   hasha dla nieznanego konta oraz ograniczenia formatu tokenu.
3. **Pola całkowitoliczbowe przyjmowały konwersje float/bool/tekst.** Wymagane są
   ścisłe int dla kwot, ilości i identyfikatorów w modelach żądań.
4. **Adres, nazwa i profil mogły składać się ze spacji.** Białe znaki są usuwane
   przed sprawdzeniem minimalnej długości. Nieprawidłowy adres nie rezerwuje towaru.
5. **Błędy walidacji zawierały przesłane wartości `input`.** Odpowiedzi zawierają
   wyłącznie lokalizację, typ i opis błędu, bez wartości i kontekstu danych.
6. **Brakowało limitu wielkości i pamięci żądania.** Limit wynosi 1 MiB, obejmuje
   strumień bez Content-Length. Sprawdzono także 30 tys. fragmentów jednego żądania.
7. **Nieobsłużone błędy serwera nie miały pełnej polityki odpowiedzi prywatnej.**
   Zwracany jest ogólny JSON 500, bez szczegółów wyjątku, z no-store i nagłówkami ochrony.
8. **Jedną pozycję przesyłki można było zwrócić osobnym endpointem.** Zwrot po
   winie dostawcy wymaga teraz obsługi całej przesyłki atomowo.
9. **Klucz zdarzenia klienta mógł kolidować z cudzym albo wewnętrznym zwrotem.**
   Klucze z API są oddzielone według zamówienia i hashowane.
10. **Ponowienie zdarzenia mogło akceptować uszkodzony stan finansowy.** Spójność
    jest sprawdzana zarówno w maszynie stanów, jak i w trwałym magazynie zdarzeń.
11. **Audyt odrzucał prawidłowy zwrot po anulowaniu.** Uwzględnia oba dozwolone
    stany końcowe: nieudaną dostawę oraz anulowanie.
12. **Brakowało zwrotu pojedynczego opłaconego zamówienia.** Dodano
    `/orders/{order_id}/cancel-paid-test` i przycisk testowy. Zwrot jest pełny,
    ponowienie nie zwiększa zapasu, a obcy klient nie ma dostępu. Obejmuje tylko
    zamówienie oczekujące przed realizacją; nie zastępuje ustawowych uprawnień.
13. **Dostawa na adres mogła kosztować 0 gr.** Bez dodatniej stawki przesyłki
    zakup i wycena są odrzucane. Odbiór w punkcie pozostaje bez opłaty dostawy.
14. **Wybór rolnika znikał po wybraniu dostawy.** Selektor jest poza ukrywaną
    częścią punktu odbioru; poprawiono też zagnieżdżone etykiety HTML.
15. **Zapytania listy zamówień PostgreSQL pomijały kod paczki.** Projekcja zawiera
    `pickup_code` wymagany przez UI. Przenośny SELECT sprawdzono na SQLite;
    pełna natywna ścieżka pozostaje niezaliczona.
16. **Rekonsyliacja uznawała stan awaiting_payment za opłacony.** Stany mapowane
    są jawnie; nieznany stan nie może zostać uzgodniony jako poprawna wpłata.
17. **Miesięczny raport pomijał zwroty po anulowaniu przez klienta.** Zlicza teraz
    także customer_cancel_refund_test, bez prowizji od zwróconej sprzedaży.
18. **Narzędzia testowe mogły poświadczać zmieniony kod albo tworzyć pliki
    w projekcie.** Dodano kontrolę niezmienności źródeł, liczenie JUnit i izolację
    plików próbnych. Poprawiono dwie starsze dane testowe do obecnego kontraktu.

Dodatkowo przygotowano blokadę transakcyjną operacji jednego kupującego w
PostgreSQL, przed odczytem klucza idempotencji. **Ta ścieżka nie została jeszcze
sprawdzona na działającym PostgreSQL.**

Nowe przypadki adwersarialne wykrywały błędy mimo przejścia starej regresji:
przed poprawkami 21 z 24 przypadków granicznych nie przechodziło. W pierwszym
zestawie finansowym nie przechodziło 8 przypadków. Nie podajemy tych liczb jako
liczby niezależnych luk bezpieczeństwa.

## Test długotrwały

Scenariusze: równoczesne ponowienie zakupu, konkurencja o ostatnią sztukę,
anulowanie i zwrot, koszyk wieloproduktowy z jedną dostawą, wyścig PIN–zwrot,
płatność i wypłata testowa, cofnięcie dostępu kuriera do adresu, wylogowanie,
rozdzielenie ról i ścisłe kwoty. Baza była jednorazową SQLite. Dane były sztuczne.

Nie stwierdzono podwójnej rezerwacji ostatniej sztuki, podwójnego zwrotu,
jednoczesnego skutecznego odbioru i zwrotu ani rozjazdu zapasów i sum pieniędzy
w zakresie wykonanych scenariuszy. Nie jest to test wydajności produkcyjnej.

## Blokady środowiska i GitHub

- **GitHub:** odczyt Orgian1/WiejskaPaka zwrócił 404, a połączenie nie udostępniło
  zainstalowanego konta. Nie porównano kodu ze zdalnym HEAD i nie zapisano
  zdalnego commita. Kod pochodzi z załączonego ZIP-a. Zmiany zapisano lokalnie
  w Git; do archiwum dołączono odtwarzalny plik bundle z historią.
- **PostgreSQL:** pobrano narzędzia i zainstalowano psycopg. initdb odmówił
  działania jako root; dostępne było tylko UID 0, bez możliwości przełączenia
  użytkownika. Nie ma Dockera. Serwer nie wystartował.
- **Chromium:** pobrano dwie wersje Chrome. Starsza zgłosiła
  `socket() failed: Operation not permitted`; nowsza zakończyła się przy starcie.
  Nie zaliczono rzeczywistego UI, zrzutów ani testów fizycznego telefonu.

Przygotowany Compose obejmuje bazę testową, komplet migracji, osobną rolę bez
uprawnień administratora i nowy pakiet natywnych testów HTTP. Ten przygotowany
pakiet nie jest dowodem wykonania. Szczegóły: `docs/POSTGRESQL_TESTY_LOKALNE.md`.

## Zasady i stan projektu

Nie dodano pól telefonu. Opłata dostawy jest liczona raz na przesyłkę,
a kwoty przechowywane i liczone w groszach. PIN potwierdza wydanie, a zwrot za
niedostarczenie z winy dostawcy obejmuje 100% symulowanej wpłaty z dostawą.
Dodano widoczną informację, że PIN nie ogranicza praw konsumenta. Podstawa
sprawdzonego komunikatu: [UOKiK](https://prawakonsumenta.uokik.gov.pl/reklamacja/niezgodnosc-czy-gwarancja/).
Nie wykonano pełnego przeglądu prawnego.

Nie podłączono Neon, płatności produkcyjnych, banków, domeny ani hostingu.
Nie uruchomiono GitHub Actions ani płatnych usług. Podział 75/20/5 pozostał
funkcją testową; nie wdrożono automatycznych potrąceń ograniczających prawa konsumenta.

Dalsze bramy i braki funkcjonalne opisuje
`docs/audits/OGRANICZENIA_I_DALSZE_PRACE.md`: w szczególności natywne PostgreSQL,
Chromium, geograficzne wyszukiwanie punktów, pełna weryfikacja sprzedawcy,
opłaty za punkty, terminowe wygaszanie nieopłaconych rezerwacji, kompletna
obsługa konsumencka oraz niezależny przegląd bezpieczeństwa i ochrony danych.

## Dowody i odtworzenie

- `audit_release_regression.json` — wynik wszystkich modułów, sumy JUnit i odcisk kodu;
- `audit_release_soak_20min.json` — wynik ciągłego testu realnego HTTP;
- `audit_release_http.json`, `audit_release_security_http.json` — trasy, uprawnienia i nagłówki;
- `audit_money_properties.json` i `tests/audit_money_properties.py` — odtwarzalna arytmetyka;
- `audit_dependencies.json`, `requirements-lock.txt` — sprawdzone zależności;
- `audit_environment_blockers.json` — granice wykonania;
- `README.md` — uruchomienie lokalne oraz polecenia testów.

Wcześniejsze raporty są historią. Wyłącznie wymienione pliki release opisują
sprawdzoną tu końcową wersję. Archiwum nie zawiera baz SQLite, tokenów sesji,
plików .env, pobranych binariów ani pamięci podręcznych.

## Dodatkowa kontrola gotowego archiwum

ZIP przeszedł kontrolę CRC i zgodności źródeł. Historię odtworzono z Git bundle.
Pełna regresja świeżo rozpakowanego archiwum także zakończyła się wynikiem
**2916 PASS, 0 FAIL, 12 SKIP w 234 modułach**. To powtórzenie tych samych testów,
nie dodatkowe 2916 różnych przypadków. Dowód: `audit_package_verification_regression.json`.
Końcowe uzupełnienie archiwum obejmuje wyłącznie ten raport i metadane kontroli;
kod aplikacji pozostał zgodny z podanym odciskiem SHA256.
