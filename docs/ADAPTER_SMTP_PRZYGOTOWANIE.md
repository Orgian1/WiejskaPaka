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

Potrzebne są wciąż uprawniony wybór odbiorcy, kolejka zapisywana atomowo
z wydaniem linku, ochrona sekretów w kolejce, ograniczone ponowienia,
retencja, obserwacja błędów i odebranie dostarczeń u wybranego dostawcy.
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
