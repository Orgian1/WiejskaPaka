# Punkt wznowienia — stan 2026-10-25

Aktualna gałąź: preview/ses-feedback-service-preflight-20261025. Repo Orgian1/WiejskaPaka.
Zmiany są stosem draft PR, bez scalania i bez modyfikowania VPS. Zachowywać lokalne
niezacommitowane zmiany przy odzyskiwaniu workspace.

Gotowe: uwierzytelnione API/panel potwierdzania adresu, szyfrowane linki,
atomowe kolejkowanie obu checkoutów, ograniczone procesy SES, wspólna blokada
wysyłki i limit kroczący, blokady odbiorców, offline weryfikacja podpisu SNS v2
z jawnie zatwierdzonym pinem oraz transakcyjne przetwarzanie jednoznacznego SES
z deduplikacją. Brak listenera HTTP, prawdziwych pinów i aktywacji na serwerze.

Bieżący pakiet lokalny: 74/74, bez błędów/pominięć, 7 izolowanych modułów.
Nowy raport: docs/audits/feedback_config_2026-10-25/local-summary.json.
Dodano chroniony zewnętrzny plik konfiguracji, rotację pinów i komendę kontroli
bez DB/sieci. Nie ma jeszcze odbiornika ani rzeczywistej konfiguracji AWS.
Anonimowy audyt rzeczywistego HTTP: 107/107 tras niepublicznych zablokowanych.
Raporty: docs/audits/pinned_feedback_2026-10-25/.

W Windows poprzednika (40119699868) były 3 błędy: dwa audyty nie uwzględniały
publicznego GET opcji weryfikacji, trzeci oczekiwał starej listy skryptów.
Odtworzono i naprawiono je, zachowując autoryzację tras prywatnych. Nie deklarować
zakończenia aktualnej pełnej regresji przed sprawdzeniem nowego CI.

Następne zadania:
1. Sprawdzić CI tej gałęzi, w tym native PostgreSQL i pełny Windows.
2. Operacyjne dostarczanie/rotacja pinów (loader i snapshot już gotowe), nie przez
   żądanie. Kontrola konfiguracji nie zatwierdza łańcucha CA dowolnego certyfikatu.
3. Odbiornik zdarzeń z ograniczoną polityką SNS i prywatnym archiwum REVIEW/starych
   zgłoszeń. Nie udostępniać bezpośrednio funkcji block ani przyjmować flag verified.
4. Korelacja identyfikatora SES dla ukrytych odbiorców, monitorowanie i harmonogram.
5. Sekrety SMTP poza kodem, rzeczywisty test własnej skrzynki, wdrożenie po kopii
   i pełne testy na VPS. Wszystkie funkcje nadal domyślnie wyłączone.

Domena wiejskapaka.pl została potwierdzona przez użytkownika w SES eu-north-1.
Nie oznacza to potwierdzenia limitów/trybu produkcyjnego konta ani adresów klientów.
Nie mamy tutaj rzeczywistych danych SMTP. Nie modyfikować VPS bez aktualnego
zakresu wdrożenia. Szczegóły: PODPISY_SNS_I_ZDARZENIA_SES_2026-10-25.md.

Szczegóły ostatniego pakietu: KONFIGURACJA_ZAUFANIA_SNS_2026-10-25.md.


Aktualizacja diagnostyki Windows 2026-10-25:
- CI 40167641983: PostgreSQL 16/17, Chromium i windows_recovery SUCCESS;
  pełny Windows: 4392 passed, 1 failed, 205 skipped. Jedyny moduł błędu:
  test_sns_pinned_notification.py; dawne trzy błędy audytów już nie występują.
- Parametr z testowym body >128 KiB miał równie duży automatyczny identyfikator
  pytest. Dodano krótkie jawne ids bez zmiany wejścia ani asercji. Osobny krok
  tego modułu na rzeczywistym Windows w run 40169086766 zakończył się SUCCESS.
  Wskazuje to na problem identyfikatora przypadku, a nie odrzucenia podpisu;
  pełna regresja po poprawce nadal wymaga potwierdzenia.
- Runner zachowuje tylko znane nazwy plików i numery linii z pełnego JUnit
  przed usunięciem pliku, aby długi output_tail nie usuwał lokalizacji błędu.
  Raport publikowany nadal nie zawiera treści asercji, parametrów ani ścieżek.
- Lokalnie 101/101, 5 izolowanych modułów, bez błędów/pominięć.
  Dowody: docs/audits/windows_sns_2026-10-25/. Wysyłka i VPS bez zmian.


Najnowszy etap: szyfrowane REVIEW — 2026-10-25
- Poprzednik cb3af15 ma WSZYSTKIE CI SUCCESS (40169232883): Windows 4395 passed,
  0 failed, 205 skipped; PostgreSQL 16/17 po 70/70; Chromium 50/50 i viewporty.
  Poprawka krótkich identyfikatorów testów SNS potwierdzona pełnym Windowsem.
- Nowy moduł ses_feedback_archive: jawna transakcja + savepoint, AES-256-GCM,
  osobne klucze, limit pojemności, retencja i rotacja; brak HTTP/aktywacji.
- Nowa migracja optional_ses_feedback_review.sql w manifeście/checksumach/psql.
- Nowy lokalny pakiet 99/99, bez błędów/pominięć, 7 izolowanych modułów.
- Nowy native test współbieżnej pojemności PostgreSQL czeka na wykonanie CI.
- Dalej: potwierdzić nowe CI, loader kluczy archiwum, listener z limitem body
  i ACK po commit, obsługa starych/niezatwierdzonych zgłoszeń i monitorowanie.
Szczegóły: ARCHIWUM_ZGLOSZEN_SES_2026-10-25.md. VPS pozostaje bez zmian.


Najnowszy pakiet — odbiornik HTTP i klucze archiwum:
- Chroniony loader niezależnych kluczy z purpose, opt-in tylko do odczytu;
  check_ses_review_keys nie łączy się z DB/siecią i niczego nie aktywuje.
- Osobna fabryka ses_feedback_http.create_app, nie podłączona do backend.app:
  POST /sns/feedback; body<=128KiB, timeout odczytu, limit współbieżności;
  prawdziwy commit przed 204, wszystkie błędy przetwarzania bez ACK sukcesu.
- Lokalnie 138/138, 9 izolowanych modułów, bez błędów/pominięć. Raport:
  docs/audits/feedback_http_keys_2026-10-25/local-summary.json.
- Nowy native test HTTP/commit po PostgreSQL czeka na faktyczne wykonanie w CI.
- CI poprzednika (40173177311) PostgreSQL 16/17, Chromium, szybki Windows SUCCESS;
  pełny Windows podczas sprawdzania nadal IN_PROGRESS.
- Dalej: sprawdzić nowe CI i pełny Windows poprzednika, operacyjny loader połączeń
  DB/procesu i kontrola historycznych kluczy, HTTPS/proxy, realne piny/polityka SNS,
  monitorowanie i retencja. Brak konfiguracji AWS/aktywacji/wdrożenia na VPS.
Szczegóły: ODBIORNIK_SNS_I_KLUCZE_ARCHIWUM_2026-10-25.md.


Najnowszy pakiet — zachowane klucze i Windows:
- Workspace odtworzony przez GitHub, tree 7f3a7ba dokładnie równy PR #37.
- CI poprzednika 40174219320: PG16/17, Chromium i szybki Windows SUCCESS;
  pełny Windows 4456 passed/1 failed/215 skipped, moduł ses_feedback_http.
  Skrócono ids dużego payloadu HTTP; maksymalna nazwa testu 106 znaków.
  Dla dużych parametrów zawsze stosować jawne krótkie ids.
- Nowa prywatna funkcja ses_review_key_check.check_retained sprawdza rzeczywiste
  odszyfrowanie zapisanych niewygasłych rekordów z proponowanym zestawem kluczy;
  READ ONLY, bez rotacji, plików/sieci/writes, limit metadanych i jeden payload naraz.
- Lokalnie 139/139, 8 izolowanych modułów, bez błędów/pominięć. Nowy native
  PostgreSQL READ ONLY test zebrany; wykonanie czeka na nowe CI.
- Kontrola nie obejmuje kopii, brakujących historycznych rekordów i przyszłych
  zapisów; nie usuwać dawnych kluczy ani nie uruchamiać usługi na jej podstawie.
- Dalej: CI (w tym Windows), operacyjny loader DB/procesu, HTTPS/proxy, prawdziwe
  piny/polityka SNS/subskrypcja, monitoring i retencja. VPS bez zmian.
Szczegóły: KONTROLA_ZACHOWANYCH_KLUCZY_SES_2026-10-25.md.


Najnowszy etap — baza odbiornika:
- ses_feedback_database: chroniony plik JSON, tylko loopback i jawne nazwy testowe;
  ładowanie bez połączenia. Każdy Target sprawdza tę samą sesję READ ONLY: bazę,
  flagi roli, tabele, uprawnienia i ustawienia, ze stałymi timeoutami/search_path.
- check_ses_feedback_database domyślnie DISABLED; --connect to tylko jawna sonda,
  bez uruchomienia HTTP, migracji/zapisu, AWS, SMTP lub modyfikowania VPS.
- 177/177 lokalnie, 9 izolowanych modułów, zero fail/skip. W tym 38 przypadków
  adaptera; sondy unit są fake, rzeczywisty nowy test PostgreSQL czeka na CI.
- Native moduł ma 70 zebranych testów; nowy przypadek używa prawdziwego Target
  w samodzielnym HTTP i sprawdza zapis po ACK na osobnym połączeniu.
- Poprzednik 40176160058 PG16/17, Chromium, szybki Windows i HTTP diagnostics
  SUCCESS; pełny Windows jeszcze w toku podczas kontroli.
- Dalej: nowe CI, wspólna konfiguracja procesu pin+keys+Target i kontrola
  zachowanych rekordów, launcher, HTTPS/proxy, prawdziwe piny/polityka SNS,
  procedura subskrypcji/monitoringu i retencji. Serwer niezmieniony.
Szczegóły: BAZA_ODBIORNIKA_SES_2026-10-25.md.


Najnowszy etap — wspólne przygotowanie i launcher:
- ses_feedback_service.prepare: jeden opt-in + trzy dotychczasowe, test-only;
  wczytuje snapshoty i politykę, bez połączeń. check: ważność pinów + Target +
  rzeczywista kontrola kluczy retained w READ ONLY. build_app dopiero po sukcesie.
- check_ses_feedback_service --check to jawna sonda, domyślnie DISABLED.
- serve_ses_feedback --serve: tylko loopback, preflight przed bindem, 1 worker,
  limity i brak proxy_headers/access_log; domyślnie DISABLED. Nie wywołano --serve.
- 203/203 lokalnie, 11 modułów, bez błędów/pominięć. Nowy native test trzech
  chronionych plików + PG/ASGI i złej rotacji czeka na CI; moduł ma 71 zebranych.
- Poprzednik 40176933757 PG16/17, Chromium, szybki Windows SUCCESS; full Windows
  nadal w toku podczas sprawdzania. Nie uznawać tego za pełne CI obecnej gałęzi.
- Dalej: nowe CI, konfiguracja systemd/HTTPS/proxy, prawdziwe piny i SNS policy,
  subskrypcja/monitoring/retencja, zatwierdzone wdrożenie/próba własnej skrzynki,
  potem integracja płatności. VPS, AWS i SMTP bez zmian.
Szczegóły: PRZYGOTOWANIE_PROCESU_SES_2026-10-25.md.
