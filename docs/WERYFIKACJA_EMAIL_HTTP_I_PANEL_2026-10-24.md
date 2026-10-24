# Weryfikacja adresu klienta: API, panel i prywatna kolejka

## Zmiana

Po jawnym włączeniu `WP_ENABLE_EMAIL_VERIFICATION=1` zalogowany użytkownik może
zamówić link potwierdzający adres przypisany do własnego konta. API ponownie
sprawdza sesję w transakcji zapisu. Adres ani identyfikator właściciela nie są
pobierane z żądania. Domyślnie funkcja pozostaje wyłączona.

W sekcji Bezpieczeństwo konta są stan potwierdzenia i przycisk zamówienia linku.
Link zawiera sekret we fragmencie `#verify-email=…`. Panel usuwa fragment z historii,
przechowuje sekret tylko w pamięci i wymaga zalogowania oraz jawnego potwierdzenia.
Nie zapisuje tokenu w localStorage, sessionStorage ani HTML. Przełączenie konta
czyści przechwycony sekret. Odświeżenie wymaga ponownego otwarcia linku.

API ma ścieżki `/auth/email-verification/options`, `/status`, `/request`, `/confirm`.
Potwierdzenie jest jednorazowe i ważne 15 minut. Błędne i wygasłe linki nie
potwierdzają konta. Ponowne wydanie unieważnia poprzedni token, najwcześniej po
60 sekundach. Własność adresu pozostaje niezależna od weryfikacji domeny w SES.

## Ograniczenia i bezpieczeństwo kolejki

Wydanie tokenu, jego skrót i szyfrowana AES-GCM wiadomość są zapisywane atomowo.
Szyfrowanie używa jawnie dostarczonego prywatnego pliku kluczy poza repozytorium:
`WP_ENABLE_MAIL_QUEUE=1`, `WP_MAIL_QUEUE_KEYS_FILE`. Import nie generuje kluczy.
Jeden rekord kolejki na konto ogranicza miejsce; ponowne wydanie zastępuje stary.

Trwałe godzinne limity wydawania: 5/konto, 30/adres IP, 1000/usługa.
Limity potwierdzania: 30/konto, 100/IP, 1000/usługa. Odmowy są zatwierdzane w bazie
zamiast znikać przy rollbacku. Liczniki usuwane są po godzinie, a wyczerpany limit
usługi blokuje tworzenie nowych wpisów. Kod nie odczytuje samodzielnie nagłówków
Forwarded/X-Forwarded-For. Zaufanie do proxy musi być ograniczone w konfiguracji
serwera przed udostępnieniem usługi.

Prywatna funkcja `dispatch_once` sprawdza aktualność tokenu i adresu, zatwierdza
znacznik rozpoczęcia i usuwa ciphertext PRZED SMTP. Niepewna odpowiedź lub awaria
nie powoduje automatycznej ponownej wysyłki. Stare rozpoczęte próby przechodzą
w stan niepewny. Przyjęcie przez SMTP nie jest dowodem dostarczenia do skrzynki.
Szablon wiadomości korzysta ze wspólnego transportu TLS; żądanie HTTP nie otwiera
połączenia SMTP. Testy zastępują transport, bez prawdziwych odbiorców.

Odtworzenie kopii SQLite/PostgreSQL usuwa dowody własności adresów, wygasza
niewysłane linki i blokuje ponawianie rozpoczętych prób. Źródłowa baza nie jest
zmieniana przez odtwarzanie. Zmiana adresu konta nie jest jeszcze funkcją API;
przyszła implementacja musi usuwać dowód i kolejkę przy KAŻDEJ zmianie adresu,
w tym przy powrocie do poprzedniego adresu.

## Migracja i dalsze kroki

`optional_email_verification.sql` jest opcjonalną, ręcznie stosowaną migracją.
SQLite tworzy tabele tylko po jawnym włączeniu funkcji; PostgreSQL wymaga ich
wcześniejszego przygotowania. Preflight sprawdza obecność trzech tabel.
Poprawiono szablon nowej bazy: wcześniejszy wpis kolejki zakupów znajdował się
dwukrotnie, w tym przed tabelami bazowymi. Nowy test wymaga dokładnie kolejności
manifestu bez duplikatów.

NIE uruchomiono usługi pocztowej, nie skonfigurowano danych SMTP i nie wysłano
wiadomości do SES. Brakuje jeszcze ograniczonego procesu/komendy obsługującej
kolejkę na serwerze, atomowego podłączenia kolejki zakupów do checkoutu,
monitorowania odrzuceń/skarg oraz testu rzeczywistej skrzynki. VPS bez zmian.

Dodano testy natywne PostgreSQL (potwierdzenie równoległe, restart, limity,
przyjęcie/niepewna wysyłka) i Chromium (320/1280 px, link, logowanie, potwierdzenie,
wylogowanie). Ich wyniki należy oceniać oddzielnie od lokalnych testów SQLite.
