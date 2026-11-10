# Szyfrowane archiwum zgłoszeń SES — etap bez aktywacji

Gałąź: preview/encrypted-ses-review-20261025. Brak zmian VPS, listenera HTTP,
SMTP, konfiguracji AWS ani automatycznego zadania. To prywatny moduł odbioru
w transakcji, nie działający punkt odbiorczy SNS.

## Zachowanie

`backend/ses_feedback_archive.receive` przyjmuje oryginalne bajty SNS oraz
niezależnie zatwierdzoną konfigurację pinów. Istniejący proces ponownie sprawdza
podpis, temat, certyfikat, świeżość i źródło SES. Nie ma flagi „verified” z żądania.
Wiadomości niepoprawne, stare i z niezatwierdzonym pinem są odrzucane bez zapisu
ich treści. Nie są automatycznie pobierane certyfikaty ani adresy URL.

Wyłącznie REVIEW zachowuje oryginalny dokument, zaszyfrowany AES-256-GCM.
Zwykłe APPLIED/IGNORED nadal przechowują tylko dotychczasowy dziennik skrótów.
Nonce jest losowy; AAD obejmuje identyfikator zdarzenia, skrót treści,
identyfikator klucza i obie daty. Prywatne `ArchiveCipher.open` sprawdza integralność;
nie ma publicznego przeglądania, odszyfrowywania ani logowania treści.

Osobny zestaw kluczy archiwum musi dostarczyć operator. Moduł nie generuje klucza
na uruchomienie, nie korzysta z domyślnych sekretów ani kluczy checkout/linków.
Rotacja wymaga zachowania starych kluczy do końca retencji odpowiednich wpisów.
Utrata klucza oznacza utratę możliwości odczytu. Plik kluczy, uprawnienia i
procedura bezpiecznej kopii pozostają częścią przyszłej integracji operacyjnej.

## Atomowość, pojemność, retencja

Caller musi rozpocząć transakcję i zatwierdzić ją przed przyszłym HTTP ACK.
Savepoint obejmuje przetworzenie SES i zapis archiwum. Nawet po przechwyceniu
wyjątku przez callera błąd szyfrowania, SQL lub pełny limit nie pozostawia
częściowego dziennika. Pozostała praca callera poza savepointem zostaje zachowana.
Nie wolno odpowiadać sukcesem po `SES_REVIEW_RECEIVE_REJECTED`.

Domyślnie: 1000 wpisów i 7 dni, jawne granice konfiguracji 1–10000 wpisów oraz
1 godzina–30 dni. Parametry są zaufaną polityką operatora, nigdy wejściem HTTP.
W PostgreSQL blokada advisory w transakcji serializuje kontrolę pojemności;
SQLite korzysta z transakcji zapisu. Usunięcie wygasłych rekordów odzyskuje miejsce.
Powtórka nie przedłuża daty zarejestrowania ani retencji. Aktualna retencja służy
też bezpiecznemu uzupełnieniu brakującego archiwum wcześniej zapisanego REVIEW.
Znane wygasłe wpisy nie są odtwarzane po powtórce w tej samej polityce.

`purge_expired` to jawna operacja w transakcji, bez timera. Usunięcie z żywej bazy
nie usuwa kopii zapasowych ani ich kluczy; polityka kopii wymaga osobnego ustalenia.
Dziennik skrótów pozostaje dla deduplikacji. Różne procesy muszą używać tej samej
polityki. Moduł nie uzgadnia odmiennego limitu/retencji z innych konfiguracji.

## Migracja i weryfikacja

Dodano `database/optional_ses_feedback_review.sql` po dzienniku SES w przeglądanym
manifeście nowej bazy testowej, checksumach i przykładzie psql. Nic nie uruchamia
migracji samoczynnie ani nie zmienia istniejącej bazy VPS.

Lokalnie 99/99, bez błędów/pominięć, 7 izolowanych modułów. W tym 27 testów archiwum:
rzeczywiste syntetyczne podpisy RSA i szyfrowanie, deduplikacja, zła sygnatura,
stare zdarzenie, niezatwierdzony pin, nadmiarowe body, pełny limit, awarie szyfrowania
oraz INSERT, cofnięcie całej transakcji, podmiana metadanych/ciphertextu,
rotacja i granica retencji. Testy migracji i audyt wydania również zaliczone.

Dodano test native PostgreSQL z dwoma równoległymi zdarzeniami i limitem jednego
wpisu: oczekiwane jedno REVIEW, jedno odrzucenie, jeden dziennik oraz możliwe
odszyfrowanie wpisu. Lokalnie tylko zebrano testy native (67 w tym module);
rzeczywiste wykonanie nowego testu musi potwierdzić CI PostgreSQL 16/17.

Poprzedni commit cb3af15a20a2005396026c3921d9003cc873da0f ma pełne zielone CI
40169232883: Windows 4395 passed / 0 failed / 205 skipped, szybki Windows 80/80,
PostgreSQL 16 i 17 po 70/70, Chromium 50/50 oraz rzeczywiste sprawdzenia viewportów.
To dowód poprzednika, nie wykonania nowego archiwum. Raporty w
`docs/audits/encrypted_review_2026-10-25/`.

Następne kroki: potwierdzenie CI archiwum, chroniony loader kluczy, listener
HTTP z ograniczeniem strumienia i ACK wyłącznie po commit, operacyjne zatwierdzenie
pinów i uprawnień tematu SNS, procedura obsługi starych/niezatwierdzonych zdarzeń,
monitorowanie, harmonogram retencji oraz dopiero później test na własnej skrzynce.
