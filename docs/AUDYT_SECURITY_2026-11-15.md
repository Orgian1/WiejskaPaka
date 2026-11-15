# Audyt bezpieczeństwa PostgreSQL i autoryzacji WiejskaPaka

Data: 15.11.2026. Baza pracy: `codex/demo-finalization-20261112`, commit
`473c75514fa4816a2d61a05c8983742f1497404a`. Gałąź poprawek:
`codex/security-audit-20261115`. Zakres nie obejmuje dostępu do VPS ani danych produkcji.

## Wynik i ograniczenie odbioru

To paczka do przeglądu, **bez deklaracji gotowości produkcyjnej**. Aktywne poprawki
API są oddzielone od ręcznie uruchamianych, odwracalnych migracji projektu RLS.
Projekt RLS przechodzi izolowane testy PostgreSQL, lecz **nie jest kompatybilny z
całym bieżącym API**. Jego aktywacja jest zablokowana. Logowanie, sesje i biznesowe
przepływy pozostają na istniejącej ścieżce, testowanej osobno bez RLS.

## Ustalenia

| ID | Waga | Ustalenie / stan |
|---|---|---|
| SEC-01 | Krytyczna przy aktywacji starego szkicu RLS | Dowolny SQL może ustawić `wiejskapaka.actor_id`. Stare helpery i plan SELECT nie uwierzytelniają SQL. Nowy projekt rozpoznaje ważny surowy token sesji po SHA256 w DB, ignoruje GUC ID/role; nie przełączono starego API na nowy model. |
| SEC-02 | Wysoka | Rola uruchamiająca właściwy backend nie była w init_postgres sprawdzana pod kątem uprzywilejowania, członkostwa i własności tabel. Dodano kontrolę przed startem PostgreSQL API. Dotychczasowy bezpieczny launcher testowy nie zastępował tej kontroli. |
| SEC-03 | Wysoka | Obecny szkic RLS ma wyłącznie SELECT i obejmuje sześć tabel. Nowe migracje obejmują wszystkie istniejące niekatalogowe tabele public, cztery operacje, FORCE RLS i domyślną odmowę zapisów. Brak jeszcze procedur biznesowych pozwalających bezpiecznie zastąpić bezpośrednie DML aplikacji — blokada wdrożenia. |
| SEC-04 | Średnia / obrona dodatkowa | Blokada produkcji była wykonywana przy imporcie aplikacji; nie była ponawiana dla żądań żyjącego procesu. Dodano kontrolę każdego żądania, niezależną od flagi płatności i nazwy trasy. Nie usunięto pierwotnej blokady startu. |
| SEC-05 | Wysoka przy niewłaściwym wdrożeniu | RLS nie ukrywa kolumn, a właściciel może go wyłączyć. Projekt roli nie ma własności ani BYPASSRLS; grant orders nie obejmuje PIN/hash, users nie obejmuje hasła, sessions nie jest czytelne przez runtime. Wymaga migracji SELECT * i bootstrap logowania przed użyciem przez API. |
| SEC-06 | Ograniczenie architektury | Część odczytów używa db() po current_user, a nowy kontekst sesji nie obejmuje wszystkich połączeń i workers. Pełna izolacja SQL nie jest dziś wdrożona. Nie rozwiązano tego przez przyznanie ogólnego bypassu systemowego. |
| TEST-01 | Naprawiono test | Lista skryptów w test_local_marketplace_ui nie uwzględniała istniejącego contact.js. Zachowano ścisłą kontrolę kolejności i defer, uzupełniając oczekiwaną listę. |
| TEST-02 | Naprawiono test | Testy publicznego katalogu resetu i katalogu poświadczeń preview pod umask 0077 tworzyły faktycznie katalog 0700. Jawne chmod(0755) zapewnia badanie odmowy dla rzeczywiście publicznego katalogu. |

| TEST-03 | Naprawiono test | Warunek gotowości zdjęć w Playwright używał wyrażenia wymagającego eval pod ścisłym CSP. Jawna funkcja sprawdza te same complete/naturalWidth bez zmiany polityki CSP aplikacji. |

## Powierzchnia API i sprawdzone reguły

Pełny inwentarz 140 tras: `AUDYT_TRAS_SECURITY_2026-11-15.json`. Strukturalnie
nie znaleziono prywatnej trasy bez zależności current_user. Jawnie publiczne
pozostają katalog/config, rejestracja/logowanie i wskazane przepływy odzyskiwania
konta oparte o token. Brak zależności nie jest automatycznie podatnością, a jej
obecność nie dowodzi poprawnej autoryzacji obiektowej.

| Obszar | Przegląd kodu i granic dostępu | Dowody regresji |
|---|---|---|
| Zamówienia | tożsamość sesji; buyer/farmer w zapytaniu lub jawne porównanie; ponowne uwierzytelnienie zapisów w transakcji; bez PIN hash w odpowiedziach | test_cross_account_isolation_b66_b70, test_b7681_cross_account_http, nowa test_security_account_matrix_http |
| Przesyłki | własność grupy i członkostwo zamówień; przydział wszystkich pozycji kurierowi; audyt administratora bez adresu i PIN | test_shipment_membership_guard, test_b8401_shipment_http_idor, test_b741_admin_shipments |
| Adresy | klient własny; sprzedawca tylko lokalizacja odbioru; kurier przydzielony, w drodze, PIN nieużyty, confirmed_at NULL; cofnięcie po odbiorze | test_delivery_access_stage08, test_delivery_privacy_stage09, test_address_delivery_http, test_rls_security_postgres |
| Portfele / wypłaty | konto wynikające z sesji, extra=forbid, PIN/hasło i limity, oddzielna rola admin do zakończenia; brak hash w snapshot | test_wallet_preview_http, test_wallet_withdrawal_lifecycle, test_payout_write_guards_38_42, nowa macierz API i test odmowy SQL zmiany salda |
| Dokumenty zakupowe | właściciel buyer/farmer; zgodność grupy; snapshot warunków bez adresu dostawy i PIN; admin ma osobny audyt | test_purchase_records_http, test_purchase_record_http_restart, test_accounting_write_auth_43_47 |
| Panel admin | jawny require(admin), rejestracja nie dopuszcza admin; cudzy bearer i nagłówki X-Role/X-User-Id nie zmieniają roli | test_admin_seller_review, test_b741_admin_shipments, nowa macierz API |
| Sesje i login | istniejące haszowanie, wygasanie, odwołanie, limity prób; nowy resolver działa bez wcześniejszego actor_id; stary login nie jest uruchamiany z projektowanymi restrykcjami RLS | test_session_security_http, test_account_security_http, test_password_reset, natywne test_postgres_full_api_optin bez RLS |
| Tryby testowe | wszystkie trasy są blokowane w production/prod/live i nieznanym WP_ENV przy każdej płatniczej fladze 0/1 | test_security_environment_boundary |

Nie potwierdzono kompletności wszystkich możliwych kombinacji IDOR w 140 trasach.
Tabela wskazuje faktyczne dowody, a inwentarz zachowuje manual_review_required.
Nie znaleziono w sprawdzonych odpowiedziach nowego wycieku pin_hash/tokenów lub
cudzego adresu. To nie zastępuje dynamicznego audytu całej instalacji.

## RLS: czego nie uznawać za zaliczoną zgodność

Testy izolacji SQL uruchamiają projektowane polityki na świeżym, lokalnym klastrze
z pełnym zweryfikowanym schematem projektu. Oddzielne natywne testy API sprawdzają
istniejący backend z ograniczoną rolą, **bez nowych polityk**. Nie sumować tych
wyników w twierdzenie „całe API działa z RLS”. Migracje w security_review nie są
wpisane do istniejącego manifestu i wymagają osobnego kroku zgodności.

Procedury systemowe, workers, bootstrap login/register/reset i precyzyjne zapisy
finansowe są koniecznymi pozostałymi pracami przed aktywacją. Zamiast fałszywie
bezpiecznych polityk `owner_id = actor_id FOR ALL` projekt odmawia tych zapisów.

## Pozostałe ryzyka i warunki zamknięcia

1. Zintegrować i przetestować całe API z RLS, w tym pre-auth, wszystkie połączenia,
   odnowienia/revocation sesji i zadania tła. Brak tej zgodności blokuje 002.
2. Zastąpić bezpośrednie DML pieniędzy/PIN/dokumentów ograniczonymi operacjami;
   nie zmieniać prowizji, groszy, odbioru ani zwrotów. Nie dodawać flagi admin GUC.
3. Zweryfikować rzeczywisty inwentarz ról/ACL/owner i SECURITY DEFINER w klonie;
   kod nie stanowi wyniku audytu konfiguracji produkcji.
4. Oddzielić loginy migration/API/jobs i ich sekrety. Zweryfikować backup,
   odtworzenie, minimalne granty, domyślne uprawnienia i ustawienia logowania.
5. Brak pełnej ochrony przed przejęciem procesu API lub kradzieżą ważnego tokenu;
   potrzebne ograniczenie logów, sekretów, transportu i infrastruktury.
6. Rejestrować oraz usunąć rzeczywiste FAIL/TIMEOUT z pełnej regresji przed odbiorem.
   Nie utożsamiać SKIP natywnego PostgreSQL z wykonaniem testu.

Instrukcja wdrożenia i rollbacku: `BEZPIECZENSTWO_POSTGRES_WDROZENIE_2026-11-15.md`.
Dokładne wyniki bieżącego przebiegu: `SECURITY_TEST_RESULTS_2026-11-15.json` oraz
uzupełnienie wyników poniżej po zakończeniu uruchomionych procesów.

## Wyniki końcowe — kod 5470741

| Zestaw | PASS | FAIL | SKIP |
|---|---:|---:|---:|
| Pełna regresja, 392 moduły, izolacja per moduł | 4881 | 0 | 100 |
| Natywny PostgreSQL: 93 API + 2 adapter, pełne ponowienie | 95 | 0 | 0 |
| Dodatkowe sondy środowiska PostgreSQL | 2 | 0 | 0 |
| Rozszerzone role Chromium z mock API, 12 scenariuszy | 4 | 0 | 0 |
| Projekt RLS na rzeczywistym PostgreSQL, także rollback | 31 | 0 | 0 |
| Dodatkowy historyczny browser/backend bridge | 0 | 1 | 0 |

95 natywnych testów PostgreSQL, dwie sondy PostgreSQL i jeden rozszerzony test
przeglądarkowy uzupełniły **98 ze 100 SKIP** pełnego zestawu. Pozostałe dwa SKIP
to odmowa pracy z kluczami na systemach nie-POSIX; środowisko ma Linux/POSIX.
Efektywne pokrycie tego zestawu to **4979 PASS, 0 FAIL, 2 SKIP**. Wynik 31 RLS
oraz trzy z czterech testów rozszerzonych występują już w pełnym zestawie — nie
należy sumować wszystkich wierszy jako unikalnych przypadków.

Osobny `python -m scripts.check_browser_backend_bridge` pozostaje **FAIL**:
historyczny harness oczekuje `(rola)` w #identity, podczas gdy obecny interfejs
wyświetla e-mail. To narzędzie spoza powyższego pełnego zestawu. Nie zmieniono
produktu, aby dopasować go do starego oczekiwania. Bieżące rzeczywiste testy
browser/HTTP w pełnym zestawie przechodzą. Ten otwarty problem jest również
zapisany w JSON wyników i nie został ukryty przez zbiorcze „0 FAIL”.

Pierwsza próba ośmiu równoległych części została przerwana po przekroczeniach
czasu na limicie dwóch CPU; zastąpił ją kompletny przebieg dwóch części. Po
naprawie przygotowania testów powtórzono zmienione moduły, wykorzystując
weryfikowane hashem PASS niezmienionych modułów. Obie części końcowego raportu
mają complete=true i sources_unchanged=true oraz zgodny fingerprint aplikacji.
Dwa początkowe błędy natywnego backupu wynikały z braku pg_dump w PATH; po
wskazaniu klientów PostgreSQL 16.2 przeszły dwa ponowienia, a następnie cały
95-przypadkowy zestaw na końcowym kodzie. `pip check` i `git diff --check`: PASS.

Przetestowany kod: `5470741fce44e8888f421b868b17e48ab55d11fa`. Końcowy commit
raportu zmienia wyłącznie dokumentację i wynikowy JSON. Środowisko: Python 3.12,
PostgreSQL 16.2 z pgserver 0.1.4, lokalne jednorazowe klastry, Chromium i SQLite
per moduł. Nie wykonano wdrożenia, nie użyto produkcyjnego DSN ani sekretów VPS.
