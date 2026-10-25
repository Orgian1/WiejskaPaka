# Punkt wznowienia — stan 2026-10-25

Aktualna gałąź: preview/encrypted-ses-review-20261025. Repo Orgian1/WiejskaPaka.
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
