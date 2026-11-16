# Raport końcowy — reklamy portfela

PR: [#63](https://github.com/Orgian1/WiejskaPaka/pull/63), oparty na gałęzi [#62](https://github.com/Orgian1/WiejskaPaka/pull/62). Weryfikowany kod i testy: `fc1b3ef75b71a7f7fb9f482b21766883a559311c`; hash aplikacji: `8596b281ef53f0185ce28e82691957feaffc828d71562a774e1306172ccb1b9c`. Po testach zmieniono wyłącznie dokumentację wyników. Nie modyfikowano VPS, bazy produkcyjnej ani rzeczywistych płatności PayU. Nie deklarujemy gotowości produkcyjnej aplikacji.

## Dostarczona funkcja

Klient i sprzedawca otrzymują reklamę po kliknięciu „Portfel”. Duży, responsywny modal ma oznaczenie „Reklama”, licznik 5–1 i wyłączony X. Po pięciu sekundach otwiera portfel automatycznie. Odświeżanie salda i operacje portfela nie wywołują reklamy. Brak kampanii, błędy i dwusekundowy timeout otwierają portfel bez reklamy. Wylogowanie i zmiana konta unieważniają stare żądania i usuwają modal.

Limit jednej emisji na 30 minut jest wspólny dla konta i trwały pomiędzy sesjami, urządzeniami oraz restartem aplikacji. Rekord konta jest blokowany w transakcji PostgreSQL, a czas pochodzi z bazy. Dwa równoczesne wejścia z oddzielnie zalogowanych sesji dają dokładnie jedną emisję. Unikalny klucz wejścia uniemożliwia powtórne naliczenie, również po upływie limitu; kliknięcie jest liczone raz na emisję.

Panel administratora obejmuje zdjęcia, reklamodawcę, link, harmonogram, włączanie/wyłączanie, edycję, logiczne usunięcie, kolejność rotacji, stronicowanie i zagregowane statystyki. Obrazy są ponownie kodowane bez metadanych; linki i daty podlegają walidacji. Nie ma HTML reklamodawcy, zewnętrznych pikseli ani przekazywania danych konta. Link używa `noopener noreferrer sponsored` oraz `no-referrer`.

Dostarczono osobne tabele, migracje up/down i polityki ENABLE/FORCE RLS. Tożsamość nadal pochodzi z aktywnej sesji i podpisanych uprawnień SQL z PR #62. Fałszywe `actor_id` lub role w GUC nie dają dostępu do cudzych limitów/emisji ani zapisu kampanii. Fizyczna rola aplikacji nie jest właścicielem tabel i nie otrzymuje bezpośredniego DML. Nie zmieniono prowizji, PIN-u, sald, zamówień, wypłat ani zasad rozliczeń w groszach.

## Wyniki testów

| Zestaw | PASS | FAIL | SKIP |
| --- | ---: | ---: | ---: |
| Pełna regresja: 397 modułów / 5060 przypadków | 4955 | 0 | 105 |
| Te same unikalne przypadki po uzupełnieniu testów opcjonalnych | **5058** | **0** | **2** |
| Pełny odbiór API i prób SQL na PostgreSQL 16.2 z FORCE RLS | 152 | 0 | 0 |
| PostgreSQL przed migracją RLS i sondy środowiska | 97 | 0 | 0 |
| HTTP reklam: uprawnienia, harmonogram, dwa urządzenia, statystyki, walidacja, restart | 14 | 0 | 0 |
| Chromium reklam: 320/1280 px, klient/sprzedawca, timer, panel, konto i awarie | 6 | 0 | 0 |
| Końcowy odbiór reklam na PostgreSQL: oddzielne sesje, spoofing, zapisy, migracje i rollback | 10 | 0 | 0 |
| Rozszerzone role Chromium z mock API: 12 scenariuszy | 4 | 0 | 0 |

Zestawy częściowo się pokrywają — nie należy sumować ich liczników. Drugie podsumowanie zastępuje pominięte przypadki wynikami tych samych modułów uruchomionych z odpowiednimi opcjami. Dwa pozostałe SKIP to warianty nie-POSIX w `test_mail_queue_key_backup.py` i `test_reset_mail_keys.py`; środowisko testowe jest Linux/POSIX.

Na rzeczywistym PostgreSQL potwierdzono poprawną odpowiedź **2xx dla wszystkich 146/146 tras API**, w tym sześciu tras reklam. Odbiór obejmuje dotychczasowe zamówienia, dostawy, portfel, wypłaty, dokumenty, sesje, logowanie i zadania automatyczne. Ręczny scheduler został sprawdzony w dozwolony poniedziałek; nie zmieniono reguły kalendarza.

Dodatkowy scenariusz Chromium → rzeczywisty backend FastAPI przeszedł 88 żądań API, w tym PIN, przypisanie kuriera, odebranie dostępu do adresu oraz idempotentny zwrot. Ten dodatkowy scenariusz korzysta z transportu in-process; zestaw PostgreSQL działa przez rzeczywisty TCP HTTP. `pip check` i `git diff --check`: PASS. Ostrzeżenie deprecjacyjne istniejącego `TestClient/httpx` nie spowodowało błędów.

Pełne zestawienie modułów, ich hashy, liczników, wyników dodatkowych oraz statusów tras: [REKLAMY_PORTFELA_WYNIKI_2026-11-16.json](REKLAMY_PORTFELA_WYNIKI_2026-11-16.json). Sprawdzono aktualność hashy aplikacji i wszystkich modułów końcowej regresji.

## Pozostałe ograniczenia i ryzyka

Nie pozostały niezaliczone testy funkcjonalne w wykonanych zestawach. Przed przyszłym wdrożeniem nadal potrzebne są przegląd i próba na kopii docelowej bazy: rzeczywiste ACL, właściciele, klucz gateway, odtworzenie kopii oraz opóźnienia i obciążenie. Lokalne wyniki nie znoszą wcześniejszych ograniczeń produkcyjnych WiejskaPaka.

- Emisje oznaczają zatwierdzone wydanie banera przez serwer, nie dowód obejrzenia. Zerwanie połączenia po zatwierdzeniu może zużyć limit bez pokazania reklamy. Chroni to przed duplikatami.
- Reklama nie jest mechanizmem autoryzacji finansowej; zmodyfikowany klient może ominąć prezentację. Zawieszona karta może zamknąć modal dopiero po wznowieniu JS.
- Historyczne emisje wymagają decyzji o retencji. Usunięcie kampanii zachowuje dane statystyczne w bazie, a pełny SQL rollback usuwa dane reklam po wymaganej archiwizacji.
- Linki wymagają nadzoru administratora. Dobrowolne przejście do zewnętrznej strony ujawnia jej zwykłe dane połączenia, ale aplikacja nie przekazuje danych konta ani referrera.
- Testy telefonu wykonano w responsywnych widokach Chromium; nie wykonano testu na fizycznym urządzeniu iOS/Safari ani dwóch nie-POSIX wariantów na Windows.

## Wdrożenie i rollback

Instrukcja: [REKLAMY_PORTFELA_2026-11-16.md](REKLAMY_PORTFELA_2026-11-16.md). Migracje: `database/security_rls/002_wallet_ads.up.sql` i `.down.sql`. Migracja wymaga świadomej deklaracji potwierdzonej zgodności API i nie jest wykonywana automatycznie przy starcie aplikacji. Testy wykonały upgrade/rollback, odrzucenie nieznanych polityk i porównanie nienaruszonych rekordów finansowych.

Preferowane wycofanie zachowuje dane: wyłączyć kampanie i przywrócić kod poprzedniej wersji, pozostawiając tabele do przeglądu. Pełny rollback SQL wykonywać dopiero po zatrzymaniu API/workerów i archiwizacji danych reklam. W tej pracy niczego nie wdrożono.
