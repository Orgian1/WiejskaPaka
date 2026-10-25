# Wspólna kontrola i jawny launcher odbiornika SES

Gałąź preview/ses-feedback-service-preflight-20261025. Brak wdrożenia na VPS,
konfiguracji AWS, prawdziwych poświadczeń, wysyłki SMTP lub uruchomienia usługi.
Kod uruchamiania przetestowano bez otwierania portu; testy HTTP korzystają z ASGI.

## Przygotowanie i kontrola

`backend.ses_feedback_service.prepare` domyślnie zwraca None i nie czyta plików
ani nie otwiera DB. Wymaga jawnie WP_ENABLE_SES_FEEDBACK_SERVICE=1, WP_ENV=test
lub testing i trzech flag: WP_ENABLE_SES_FEEDBACK_CONFIG,
WP_ENABLE_SES_REVIEW_KEYS, WP_ENABLE_SES_FEEDBACK_DATABASE (wszystkie =1).
Niepełne ustawienia są odrzucane przed pierwszym odczytem prywatnego pliku.

Wczytuje istniejące chronione snapshoty pinów, niezależnych kluczy oraz lokalnej
bazy testowej przez dotychczasowe loadery. Nie zmienia os.environ, plików lub bazy.
Wspólna polityka ma domyślne wartości i granice:
- WP_SES_REVIEW_MAX_RECORDS: 1000, zakres 1–10000;
- WP_SES_REVIEW_RETENTION_SECONDS: 604800, zakres 3600–2592000;
- WP_SES_FEEDBACK_BODY_TIMEOUT: 5, zakres 1–30;
- WP_SES_FEEDBACK_MAX_INFLIGHT: 8, zakres 1–32.

Akceptowane są tylko kanoniczne dodatnie dziesiętne stringi. Błędna polityka
zatrzymuje przygotowanie przed odczytami. Przykład env zawiera wyłącznie ścieżki
oraz wyłączone flagi, bez sekretów. Prepared ukrywa obiekty konfiguracji w repr.

Jawne `Prepared.check` ponownie sprawdza ważność co najmniej jednego zatwierdzonego
certyfikatu na bieżącą chwilę, otwiera Target (który sonduje tę samą sesję bazy)
i w READ ONLY sprawdza rzeczywiste odszyfrowanie zachowanych niewygasłych rekordów.
Połączenie jest zamykane także przy błędzie. Sukces zawiera tylko
CONFIGURATION_VALID i retained_records; wyjątek jest stały SES_FEEDBACK_SERVICE_REJECTED.
Nie pobiera certyfikatów ani nie ustanawia ich zaufania CA. Nadal wymagane jest
niezależne zatwierdzenie pinów i uprawnień tematu przez operatora.

Kontrola kluczy dotyczy odczytanych rekordów w żywej bazie, nie kopii, brakujących
historycznych danych lub przyszłych zapisów innych procesów. Operator musi
koordynować wymianę snapshotów i wyłączenie dawnych writerów. Wynik nie zezwala
na usunięcie starych kluczy ani nie oznacza gotowości do produkcji.

`Prepared.build_app` najpierw wykonuje powyższą kontrolę, następnie konstruuje
samodzielną aplikację HTTP z tymi snapshotami i polityką. Nie otwiera portu.
Zły historyczny materiał, wygasłe piny lub błąd bazy uniemożliwiają jej utworzenie.

## Jawne komendy

`python -m scripts.check_ses_feedback_service` domyślnie DISABLED, bez pracy.
Dopiero --check zezwala na odczyt chronionych plików i sondę READ ONLY. Nie tworzy
aplikacji HTTP, nie wiąże portu. Błąd zwraca CONFIGURATION_REJECTED i exit 1.

`python -m scripts.serve_ses_feedback` również domyślnie DISABLED. --serve wymaga
kompletnej konfiguracji i przejścia kontroli przed uruchomieniem uvicorn.
Dopuszcza wyłącznie 127.0.0.1 lub ::1 i port 1–65535 (domyślnie 8011).
Jeden worker, brak reload/access_log, brak zaufania proxy_headers, limit_concurrency
32, backlog 32, timeout_keep_alive=5 i graceful_shutdown=5. Wewnętrzny limit
równoległych odbiorów pozostaje domyślnie 8. Błąd to LAUNCHER_REJECTED/exit 1;
normalne zakończenie uruchomionego procesu: STOPPED.

Nie wywołano --serve w tej sesji. Nie zainstalowano systemd, proxy, HTTPS ani
reguł firewalla. Publiczny odbiór SNS wymaga osobnego przeglądu konfiguracji
HTTPS/proxy i limitów zasobów. Timeouty DB/body są częściowymi ograniczeniami,
nie jedną gwarantowaną długością całego startu lub requestu. Nie ma auto-retencji,
monitoringu, automatycznej subskrypcji, odnawiania pinów lub wysyłki.

## Walidacja

203/203 lokalnie, bez błędów/pominięć, 11 izolowanych modułów, sources_unchanged.
W tym 15 przypadków wspólnej kontroli i 11 launchera: brak pracy domyślnie,
niepełne opt-in, polityka, zły historyczny klucz, wygasły snapshot przed DB,
zamknięcie po błędzie, zapis HTTP po kontroli, zakaz publicznego bindu oraz brak
uruchomienia serwera po błędzie. Test launchera używa fake uvicorn.run, bez sieci.
Argumenty run zweryfikowano z sygnaturą zainstalowanego uvicorn 0.54.0.
Obie domyślne komendy wykonano: DISABLED.

Dodano native PostgreSQL test: trzy rzeczywiste chronione pliki, prepare/check,
ASGI POST z prawdziwym zapisem PG, odczyt retained_records=1 oraz odmowa build_app
po podmianie materiału pod tą samą nazwą klucza. Lokalnie tylko kolekcja:
71 testów w module native; wykonanie nowego przypadku wymaga CI PostgreSQL 16/17.

Poprzednik 7e213d9/run 40176933757 miał podczas sprawdzania SUCCESS dla PostgreSQL
16/17, Chromium i windows_recovery; pełny Windows pozostawał IN_PROGRESS.
Nie deklarować pełnej nowej regresji bez jej sprawdzenia. Dowody:
docs/audits/feedback_service_2026-10-25/.

Dalej: CI, przegląd konfiguracji procesu i HTTPS/proxy, prawdziwe piny/polityka SNS,
procedura subskrypcji, obserwowalność błędów/retencji, zatwierdzone wdrożenie i
próba własnej skrzynki. Następnie integracja płatności oraz pełny zakup na serwerze.
