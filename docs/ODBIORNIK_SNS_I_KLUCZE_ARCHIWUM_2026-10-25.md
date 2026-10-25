# Odbiornik SNS i chronione klucze — kod bez wdrożenia

Gałąź preview/ses-feedback-http-keys-20261025. Brak zmian VPS, aktywacji SMTP,
prawdziwych kluczy lub zmian AWS. Odbiornik nie jest podłączony do głównej aplikacji
ani uruchamiany automatycznie. Nie dodano procesu serwerowego lub konfiguracji proxy.

## Klucze archiwum

`backend.ses_review_keys` czyta istniejący plik POSIX poza repozytorium: zwykły plik,
aktualny właściciel procesu, brak dostępu grupy/innych (np. 0600), bez symlinku
końcowego. O_NOFOLLOW/O_NONBLOCK, kontrola fstat i limit 16 KiB zabezpieczają odczyt;
katalog/FIFO, błędny właściciel, publiczne uprawnienia i nadmiarowy plik są odrzucane.
Nie ma zapisu, generowania sekretów ani odczytów przy imporcie.

Domyślnie `WP_ENABLE_SES_REVIEW_KEYS=0`; jawna wartość `1` pozwala wyłącznie na odczyt
`WP_SES_REVIEW_KEYS_FILE`. Żadna z tych zmiennych nie uruchamia listenera.
Przykład bez sekretów: deploy/preview/ses-review-keys.env.example.

Dokument ma dokładnie pola: format (liczba 1), purpose (`ses-feedback-review-v1`),
active (identyfikator klucza), keys (mapa identyfikatorów na kanoniczne base64).
Od 1 do 8 odrębnych kluczy po 32 bajty; format kolejki bez purpose jest odrzucany.
Zduplikowane pola JSON, niepoprawne identyfikatory, niekanoniczne kodowanie,
powtórzone materiały i nieznany aktywny klucz nie przechodzą kontroli.
Purpose zapobiega przypadkowemu podaniu zwykłego pliku kolejki; nie dowodzi, że
operator nie skopiował materiału innego klucza do pliku archiwum.

`python -m scripts.check_ses_review_keys` sprawdza tylko dokument i ochronę pliku,
bez DB/sieci/aktywacji: DISABLED, KEYS_VALID albo KEYS_REJECTED. Odrzucenie daje
kod wyjścia 1. Wynik nie zawiera klucza, ścieżki ani treści wyjątku. KEYS_VALID
nie dowodzi dostępności kluczy wszystkich historycznych rekordów bazy.
Rotacja przez atomową podmianę pliku tworzy nowy snapshot; stary snapshot pozostaje
bez zmian. Stare materiały trzeba zachować do upływu retencji i polityki kopii.

## Osobna fabryka HTTP

`backend.ses_feedback_http.create_app` wymaga zaufanego FeedbackConfig,
ArchiveCipher i fabryki nowych połączeń DB. Nie odczytuje konfiguracji z żądania,
nie pobiera certyfikatów, nie potwierdza subskrypcji i nie przyjmuje flag verified.
Nie ma panelu, OpenAPI, publicznego odczytu ani odszyfrowywania. Jedyna trasa:
POST /sns/feedback. SNS text/plain z surowym JSON działa bez zaufania do nagłówka
określającego typ wiadomości; typ i pozostałe pola weryfikuje podpisana koperta.

Limit treści 131072 bajty jest sprawdzany zarówno z Content-Length, jak i podczas
strumieniowania. Domyślnie 5 sekund na odczyt (zakres 1–30), bez rozpakowywania
gzip; domyślnie 8 obsługiwanych naraz żądań (zakres 1–32) na instancję aplikacji.
Nadmiar żądań otrzymuje 503 przed odczytem body i otwarciem DB. Ograniczenie jest
lokalne dla procesu; proxy/serwer muszą zapewnić globalne limity i HTTPS.

Przetwarzanie DB odbywa się w wątku, z nowym połączeniem i transakcją. PostgreSQL
ma lokalne statement_timeout=5s i lock_timeout=1s; SQLite busy_timeout=2s.
Fabryka połączeń musi osobno zapewnić ograniczony connect_timeout, właściwą bazę,
rolę i uprawnienia. Nie ma jeszcze gotowego operacyjnego loadera połączeń/launchera.
Limit body nie jest obietnicą maksymalnego czasu całego requestu/połączenia DB.

Tylko zatwierdzona transakcja daje 204. Prawidłowa powtórka również daje 204.
Błąd podpisu/klucza/źródła, niezatwierdzony pin, stare zgłoszenie, pełne archiwum,
błąd DB lub COMMIT dają 503, bez tekstu wyjątku/treści zdarzenia. Odbiornik nie
przyjmuje starego zgłoszenia na siłę ani nie zgaduje odbiorcy. 400: błędna długość,
rozłączenie lub pusta treść; 408: timeout body; 413: nadmiar treści; 415: kompresja.
Sukces SMTP i faktyczne doręczenie nadal nie są tym samym.

## Weryfikacja i ograniczenia

Lokalnie 138/138, bez błędów/pominięć, 9 izolowanych modułów, sources_unchanged.
26 przypadków kluczy, w tym rotacja z faktycznym szyfrowaniem/odszyfrowaniem,
prywatny plik, symlink/FIFO i błędny format; 17 przypadków HTTP: zapis przed ACK,
deduplikacja, blokada odbiorcy, podpis/pin/freshness, pełne archiwum, awaria COMMIT,
limity nagłówków/strumienia, timeout niedokończonego body oraz współbieżny limit.
Audyty autoryzacji głównej aplikacji i wydania pozostają zielone.

Dodano native test HTTP na PostgreSQL z odczytem zaszyfrowanego rekordu przez
osobne połączenie po otrzymaniu 204; lokalnie wykonano tylko kolekcję (68 testów
w module native). Faktyczne wykonanie PostgreSQL 16/17 oraz Windows musi potwierdzić
CI nowej gałęzi. Raport lokalny: docs/audits/feedback_http_keys_2026-10-25/.

Poprzednik 9aad14c (PR #36, run 40173177311) miał podczas sprawdzania SUCCESS dla
PostgreSQL 16/17, Chromium i windows_recovery; pełny Windows pozostawał w toku.
To dowód poprzednika. Nie deklarować pełnej aktualnej regresji bez jej sprawdzenia.

Pozostaje: CI, operacyjna konfiguracja bazy i procesu odbiornika, zaufane prawdziwe
piny/rotacja i uprawnienia tematu SNS, ręczne potwierdzenie subskrypcji zgodną
procedurą, monitorowanie błędów i starych/pin-unknown zdarzeń, harmonogram retencji,
kontrola dostępności historycznych kluczy, HTTPS/proxy i test AWS po zatwierdzonym
wdrożeniu. W tej paczce żadne zasoby zewnętrzne nie są aktywowane.
