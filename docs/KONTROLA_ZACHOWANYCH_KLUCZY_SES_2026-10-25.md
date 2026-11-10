# Kontrola zachowanych kluczy SES i poprawka testu Windows

Gałąź preview/retained-ses-key-check-20261025. Bez aktywacji, rotacji kluczy,
wysyłania poczty, zmian AWS lub modyfikowania VPS.

## Odzyskanie i CI poprzednika

Workspace wrócił do lokalnego ffc84a3. Przy czystym drzewie odzyskano 25 plików
PR #36/#37 przez GitHub. Odtworzony lokalny commit 0963a16 ma drzewo
7f3a7ba0421705bdfe89f889e095a589ac66b9e6, identyczne z GitHub HEAD PR #37
6839fba5cb9f78c037dec932e2be2e693f65867c. Nie nadpisano niezacommitowanej pracy.

Run 40174219320: PostgreSQL 16 i 17, Chromium oraz windows_recovery SUCCESS.
Pełny Windows: 4456 passed, 1 failed, 215 skipped; jedyny moduł błędu:
test_ses_feedback_http.py. Przypadek z body 131073 bajty miał automatyczny
identyfikator pytest zawierający całe body. Nadano krótkie jawne ids, zachowując
wejścia i asercje. Maksymalna lokalnie zebrana nazwa 17 testów HTTP ma teraz
106 znaków. Dodano osobny szybki krok diagnostyczny Windows dla tego modułu,
przed szeroką regresją. Faktyczne potwierdzenie poprawki na Windows wymaga nowego CI.
Przy nowych testach dużych payloadów zawsze stosować krótkie jawne ids.

## Rzeczywiste sprawdzenie kluczy

Prywatna funkcja `backend.ses_review_key_check.check_retained` wymaga istniejącej
transakcji i proponowanego ArchiveCipher. Działa bez zapisu, w tym w transakcji
PostgreSQL READ ONLY lub SQLite query_only. Nie otwiera połączeń, nie czyta
plików, nie odszyfrowuje niczego do odpowiedzi HTTP i nie jest trasą publiczną.

Wybiera identyfikatory wyłącznie zapisanych rekordów, których expires_at > now.
Domyślnie maksymalnie 10000; jawny limit ma zakres 1–10000. Pobiera najwyżej
limit+1 małych identyfikatorów i odrzuca nadmiar przed odszyfrowaniem. Następnie
czyta i uwierzytelnia jeden ciphertext naraz, zamiast pobierać całe archiwum
plaintext/ciphertext do jednej listy. Brak rekordu podczas odczytu jest błędem.

AES-GCM i skrót treści wykrywają brak klucza, niewłaściwy materiał pod poprawną
nazwą oraz podmianę sprawdzanych danych/metadanych. Sukces ma tylko postać
`{"status":"RETAINED_KEYS_VALID","checked":N}`; dowolny błąd to stały wyjątek
`SES_RETAINED_KEYS_REJECTED`, bez treści, klucza, adresu lub ścieżki.

To kontrola odczytanych, zachowanych rekordów w żywej bazie. Nie potwierdza
kompletności historycznego archiwum ani kopii zapasowych i nie przełącza aktywnego
procesu na nowe klucze. Operator musi skoordynować zatrzymanie starych writerów,
izolację odczytu i podmianę snapshotów. Późniejsze wpisy innego procesu nie są
objęte wcześniejszym wynikiem. Wygasłe rekordy nie wymagają dawnego klucza w tej
kontroli, ale ich wpisy nie są tutaj usuwane; polityka kopii może nadal wymagać
zachowania starego materiału. Nie używać tego wyniku jako zgody na skasowanie
starych kluczy lub uruchomienie wysyłki.

## Walidacja

Lokalnie 139/139, bez błędów/pominięć, osiem izolowanych modułów, źródła bez zmian.
Obejmuje rzeczywiste szyfrowanie i odczyt na bazie query_only, złe/brakujące
materiały, zmieniony ciphertext/AAD, rotację, granicę retencji, pustą bazę,
brak transakcji i przekroczenie limitu przed odczytem payloadów. Powiązany moduł
HTTP i audyt wydania również zaliczone.

Dodano native PostgreSQL test prawdziwego odszyfrowania w READ ONLY z nowym
aktywnym kluczem oraz odrzucenia złego materiału pod starą nazwą. Lokalnie zebrano
69 testów w module native; wykonanie nowego przypadku PostgreSQL 16/17 czeka na CI.
Raporty: docs/audits/retained_keys_2026-10-25/.

Dalej: wyniki CI, operacyjny loader bazy/procesu i kontrola dostępności kluczy,
HTTPS/proxy, prawdziwe piny oraz polityka SNS, procedura subskrypcji,
monitorowanie, harmonogram retencji i dopiero zatwierdzone wdrożenie/test AWS.
