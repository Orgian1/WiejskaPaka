# Adapter SMTP — przygotowanie bez wysyłania wiadomości

Moduł backend/smtp_reset_transport.py przygotowuje wiadomość resetu oraz
pojedynczą próbę przekazania jej do serwera SMTP. Nie jest wywoływany przez
żadną trasę HTTP, lokalną skrzynkę demo ani pracownika kolejki. Zmienne
konfiguracji same w sobie nie uruchamiają poczty. Nie wysłano rzeczywistych
wiadomości podczas przygotowania i testowania tego modułu.

## Konfiguracja i granice

Przykład: deploy/preview/smtp.env.example. Domyślnie WP_ENABLE_SMTP=0.
load_config zwraca wtedy None, bez odczytu hasła lub połączenia sieciowego.
Jawny opt-in wymaga pełnej konfiguracji. Hasło znajduje się w osobnym pliku
poza projektem, bez dowiązania; na POSIX wyłącznie bieżący właściciel ma
prawa odczytu/zapisu. Maksymalnie 4096 bajtów. Login i hasło mają obsługiwać
konserwatywny zestaw drukowalnych znaków ASCII. Windows ACL nie są odbierane;
odczyt rzeczywistego sekretu w tym wariancie wymaga POSIX.

Obsługiwane są TLS od początku połączenia na 465 oraz wymagany STARTTLS
na 587. W obu przypadkach działa weryfikacja certyfikatu i nazwy serwera,
TLS minimum 1.2. Brak możliwości przełączenia na jawne hasło lub wyłączenia
weryfikacji. Limit operacji sieciowej wynosi 1–30 sekund. Login nie jest
wysyłany przed zakończeniem wymaganego TLS.

Wiadomość ma jednego odbiorcę, ustalonego nadawcę i polską treść. Link
korzysta z zaufanego, skonfigurowanego origin HTTPS, bez przyjmowania hosta
z żądania. Token występuje wyłącznie we fragmencie linku w treści wiadomości,
nie w jej temacie lub innych nagłówkach. Nie ma pól Cc/Bcc, załączników,
PIN-u paczki, telefonów ani śledzenia reklamowego. Parser adresu celowo
nie obsługuje nazw wyświetlanych, list odbiorców i adresów SMTPUTF8.

## Wyniki i ponawianie

ACCEPTED oznacza wyłącznie przyjęcie przez serwer SMTP, nie dostarczenie do
skrzynki odbiorczej. DELIVERY_UNCERTAIN oznacza zerwanie połączenia podczas
przekazywania treści bez pewnego wyniku — nie wolno ponawiać automatycznie
w ciemno. Błąd QUIT po potwierdzonym przyjęciu nie zmienia wyniku na odmowę
ani nie powoduje drugiej próby. Jawne odmowy 4xx i 5xx mają rozróżnioną
możliwość ponowienia. Zwracane wyniki zawierają jedynie ustalone kody
i wartości logiczne, bez surowych odpowiedzi serwera, adresów odbiorców,
tokenów, loginu lub hasła. Adapter nie wypisuje transkryptu SMTP.

## Co pozostaje do integracji

Aktualizacja 19.10: wybór odbiorcy dla istniejącego konta, kolejka zapisywana
atomowo z linkiem, zaszyfrowane ładunki, ograniczone ponowienia, retencja
i kwarantanna po odtworzeniu są już zaimplementowane i przetestowane.
Testowa trasa HTTP potrafi zapisać zadanie w PostgreSQL. Nie należy ponownie
otwierać tych prac jako brakujących funkcji adaptera.

Pozostają uruchomienie adaptera przez jawnie skonfigurowany proces usługowy,
jego konto i ograniczona rola, nadzorca oraz odbiór dostarczeń u dostawcy.
Nie łączyć wprost testowego issue() z SMTP: demo generuje losowe linki
również dla nieznanych adresów. Trzeba zachować ogólną odpowiedź HTTP,
bez wysyłania wiadomości do nieuprawnionych odbiorców.

Testy korzystają z serwera zastąpionego obiektem w pamięci: sprawdzają
kolejność TLS i uwierzytelnienia, politykę certyfikatów, walidację wejścia
oraz niejednoznaczny wynik DATA/QUIT. Nie są testem rzeczywistego handshake
z dostawcą, DNS/SPF/DKIM/DMARC ani dostarczenia do skrzynek.

Podstawa techniczna: oficjalna dokumentacja Python 3.12
https://docs.python.org/3.12/library/smtplib.html oraz
https://docs.python.org/3.12/library/ssl.html — sprawdzona 18.10.2026.

Projekt atomowości, dzierżaw i obsługi niepewnego wyniku opisuje
KONTRAKT_KOLEJKI_POCZTY.md. To wymagania następnego etapu, bez implementacji.

Powyższy opis kontraktu jest historycznym stanem przygotowania adaptera.
Aktualne wykonanie opisują checkpointy z 19.10 oraz
POZOSTALE_PRACE_DO_PODGLADU_2026-10-19.md.

Część kontraktu zrealizowano 19.10.2026 w odłączonej kolejce SQLite:
KOLEJKA_RESETU_SQLITE.md. Adapter i kolejka współpracują w testach z
transportem w pamięci; nie są podłączone do tras aplikacji ani dostawcy.

Kolejny etap obejmuje odłączone wykonywanie PostgreSQL i prywatny loader
kluczy; aktualny zakres i wyniki wskazuje
RAPORT_KOLEJKI_POSTGRESQL_I_KLUCZY_2026-10-19.md. Wysyłka aplikacji
i odbiór u dostawcy pozostają oddzielnym zadaniem.
