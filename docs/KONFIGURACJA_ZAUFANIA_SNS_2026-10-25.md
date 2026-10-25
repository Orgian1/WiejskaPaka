# Chroniona konfiguracja zaufania SNS i rotacja pinów

## Gotowe

`backend/ses_feedback_config.py` odczytuje zatwierdzony przez operatora plik
poza repozytorium. Domyślnie jest wyłączony. Włączenie
WP_ENABLE_SES_FEEDBACK_CONFIG=1 pozwala wyłącznie na odczyt pliku podanego w
WP_SES_FEEDBACK_CONFIG_FILE, nie uruchamia odbiornika ani przetwarzania w tle.

Wymagany jest istniejący regularny plik POSIX należący do procesu, bez dostępu
grupy/innych użytkowników (typowo 0600/0400). Dowiązania, pliki w repozytorium,
nieprawidłowe uprawnienia i za duże dokumenty są odrzucane. Rozmiar ograniczono
do 96 KiB. Błędy zwracają stały kod bez treści, nazwy pliku czy danych konta.
Kod niczego nie tworzy, nie pobiera certyfikatów i nie łączy się z siecią.

Format JSON ma dokładnie pola:
- format: liczba całkowita 1;
- topic_arn: zatwierdzony temat SNS;
- source_arn: zatwierdzona tożsamość SES z tego samego konta/regionu;
- max_age_seconds: dozwolona świeżość w granicach weryfikatora;
- pins: od 1 do 4 par certificate_url/certificate_pem.

Każdy pin przechodzi wcześniejszą walidację SNS/RSA. Klucze JSON, adresy
certyfikatów i identyczne certyfikaty nie mogą się powtarzać. Co najmniej jeden
certyfikat musi być aktualnie ważny; wybrany certyfikat jest następnie ponownie
sprawdzany przy weryfikacji zgłoszenia. Pozostawienie starego pinu obok nowego
nie omija kontroli jego dat.

## Rotacja i przetwarzanie

Operator może atomowo zastąpić plik konfiguracją starego i nowego certyfikatu.
Kolejny odczyt tworzy nowy, niezmienny snapshot. Już wczytana konfiguracja nie
zmienia się w tle — wymagane jest jawne przeładowanie przez przyszły odbiornik.
Nie ma automatycznej akceptacji nowych certyfikatów znalezionych w zgłoszeniu.

Prywatna funkcja apply wybiera tylko pin z zatwierdzonego snapshotu i wymaga
zgodnego tematu. Następnie wcześniejszy moduł ponownie weryfikuje surowy podpis
i atomowo zapisuje blokadę/dziennik. Parametry zgłoszenia nie mogą podmieniać
zaufanej konfiguracji. Wspólna walidacja tożsamości SES jest używana zarówno
przy odczycie konfiguracji, jak i przy przetwarzaniu.

## Sprawdzenie bez aktywacji

```
python -m scripts.check_ses_feedback_configuration
```

Bez włączenia flagi wynik to DISABLED. Po jawnym włączeniu kontrola zwraca
CONFIGURATION_VALID oraz liczbę pinów albo stały CONFIGURATION_REJECTED.
Nie korzysta z bazy, nie zapisuje konfiguracji i nie wysyła powiadomień.
Nie ujawnia certyfikatów, ARN, adresów odbiorców ani ścieżki.
Szablon flag: deploy/preview/ses-feedback.env.example.

CONFIGURATION_VALID oznacza poprawność lokalnej konfiguracji/kluczy. NIE jest
potwierdzeniem pochodzenia dowolnego PEM z AWS ani poprawności polityki tematu.
Zaufane pozyskanie certyfikatów i kontrola łańcucha CA muszą poprzedzić ich
zatwierdzenie. Nadal trzeba ograniczyć publikację SNS do zamierzonego SES.

## Weryfikacja i dalsze kroki

74 lokalne testy zaliczone, 0 błędów/pominięć, 7 izolowanych modułów z niezmienionymi
źródłami. Wśród testów: rotacja dwóch rzeczywistych syntetycznych kluczy RSA,
niezmienność snapshotu, nieznany pin/temat, rozbieżne konto/region, błędny format,
prywatne pliki, atomowa podmiana, redakcja błędów, domyślne wyłączenie i zapis
zweryfikowanego zdarzenia. Dodano natywny test PostgreSQL z rzeczywistym odczytem
chronionego pliku; jego wynik wymaga nowego CI.

Poprzedni PR #34 przeszedł PostgreSQL 16/17, Chromium i szybki Windows; pełny
Windows przy sprawdzaniu był w toku. Wyniki te nie zastępują CI nowej zmiany.

Pozostają odbiornik/archiwum zgłoszeń, polityka publikacji SNS, operacyjna rotacja,
korelacja identyfikatorów SES, monitorowanie, harmonogram oraz rzeczywisty test
własnej skrzynki i wdrożenie. Nie zmieniono VPS i nie wysłano wiadomości do SES.
