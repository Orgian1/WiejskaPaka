# Przygotowanie resetu PostgreSQL i adaptera SMTP — 18.10.2026

Kod pakietu połączonego: 6fe0712885a7bd2db5a43319dd205f0e2adadfd3.
CI: https://github.com/Orgian1/WiejskaPaka/actions/runs/39162288218
PR: https://github.com/Orgian1/WiejskaPaka/pull/6

## Zmiana działająca w zamkniętym teście

Reset hasła można jawnie uruchomić na dedykowanym lokalnym PostgreSQL,
z prywatną skrzynką plikową poza projektem. Potrzebne są dwie flagi opt-in;
zwykłe uruchomienie PostgreSQL nadal nie włącza tej funkcji.

Blokady transakcyjne serializują limity i potwierdzenia resetu oraz
współpracują z blokadą konta podczas logowania, zwykłej zmiany hasła i
cofania sesji. Nowe testy sprawdzają ponowne użycie linku, jego wygaśnięcie,
restart API, równoległe wydania, kilka linków tego samego konta, wyścigi
z logowaniem i zmianą hasła oraz rollback po błędzie usuwania sesji.
Reset nie zmienia zamówień, ich pierwotnych warunków, PIN-ów lub klucza sejfu.

W pierwszym uruchomieniu bramki 26/27 przypadków przeszło. Scenariusz po
wymuszonym błędzie HTTP 500 próbował od razu użyć połączenia zamykanego
przez serwer. Test rozdzielono: najpierw sprawdza stan bazy, potem logowanie
przez nowe połączenie TCP. Nie zmieniono mechanizmu rollbacku, aby uzyskać
sukces. Następne wykonanie kodu 94e97c7 zaliczyło 27/27 na PostgreSQL 16;
raporty są powiązane z konkretnymi źródłami. Ten wcześniejszy etap
zaliczył także pełny Linux (3866 zaliczonych, 0 błędów, 49 pominiętych)
i Windows (3845 zaliczonych, 0 błędów, 70 pominiętych).

Instrukcja: RESET_HASLA_POSTGRESQL_TESTOWY.md.

## Adapter do późniejszej integracji

Moduł smtp_reset_transport przygotowuje pojedynczą próbę wysyłki resetu.
Wymaga TLS z weryfikacją certyfikatu, prywatnego pliku hasła i ustalonego
origin HTTPS. Błąd zamknięcia połączenia po przyjęciu wiadomości nie zmienia
wyniku na odmowę; brak pewnego wyniku DATA jest oznaczany jako niepewny,
bez zalecenia automatycznego ponawiania.

Adapter ma 30 lokalnych testów z obiektem SMTP w pamięci. Nie wykonano
prawdziwej wysyłki, DNS, handshake TLS z dostawcą ani odbioru wiadomości.
Nie jest wywoływany przez trasę HTTP lub kolejkę. Sam wpis w konfiguracji
nie podłącza go do aplikacji; domyślnie pozostaje wyłączony.
Instrukcja: ADAPTER_SMTP_PRZYGOTOWANIE.md.

## Weryfikacja pakietu

Wszystkie bramki kodu 6fe0712 zakończyły się sukcesem. Wyniki sprawdzono. Wyniki lokalne i natywne nie są sumowane; pominięcia
są raportowane oddzielnie.

| Bramka | Zaliczone | Błędy | Pominięte | Stan |
| --- | ---: | ---: | ---: | --- |
| Pełny Linux, 318/318 modułów | 3896 | 0 | 49 | sukces |
| Pełny Windows, 318/318 modułów | 3870 | 0 | 75 | sukces |
| PostgreSQL 16, rola aplikacji i HTTP | 27 | 0 | 0 | sukces |
| Chromium | 36 | 0 | 0 | sukces; także HTTP w pięciu rozmiarach |
| Szybki Windows | 80 | 0 | 0 | sukces |

Źródła podczas pełnych przebiegów pozostały niezmienione. Pominięcia
obejmują bramki wymagające innego środowiska; sam Windows pomija również
sprawdzenia uprawnień pliku POSIX. Oddzielne natywne bramki nie zastępują
tych liczb ani nie są do nich doliczane. Skrócone raporty
bez treści logów znajdują się w audits/mail_6fe0712_2026-10-18/.
Pobrane artefakty CI mają sprawdzony SHA-256 archiwum, zgodność odcisków
źródeł, complete, success oraz sources_unchanged. Oddzielny katalog
postgres_reset_94e97c7_2026-10-18 dokumentuje poprzedni etap resetu;
nie przedstawiać go jako wyniku późniejszego adaptera.

## Pozostały zakres

Nadal potrzebne są atomowa kolejka wysyłek, bezpieczne przechowywanie tokenów
w kolejce, właściwy wybór odbiorcy, weryfikacja adresu i odbiór u dostawcy.
Projekt kolejnego etapu zapisano w KONTRAKT_KOLEJKI_POCZTY.md;
nie jest to działająca kolejka. Nie wolno podłączyć wprost skrzynki demo do SMTP: demo tworzy losowe kody
również dla nieznanych adresów w celu ochrony przed ujawnianiem kont.

Nie podłączono serwera, domeny, dostawcy poczty ani rzeczywistych płatności.
Nie zmieniono prowizji, zwrotów lub opłaty dostawy. Rolnik i sprzedawca nadal
są tą samą rolą. Ten pakiet nie oznacza gotowości do rzeczywistej sprzedaży.
