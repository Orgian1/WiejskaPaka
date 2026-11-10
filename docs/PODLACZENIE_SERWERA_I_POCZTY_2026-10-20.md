# Przygotowanie serwera i poczty — 20.10.2026

Stan potwierdzony przez właściciela 19.10: domena wiejskapaka.pl już jest,
serwer został opłacony; dostęp do serwera i poczty spodziewany 20.10.
Nie kupować ponownie domeny. Poniższe kroki nie zostały jeszcze wykonane
na zakupionym serwerze. Pierwszy etap to zamknięty podgląd na sztucznych danych.

## Dane potrzebne po aktywacji

| Usługa | Dane do ustalenia |
| --- | --- |
| Serwer | System i wersja, adres IP, sposób dostępu SSH |
| Domena | Dostęp do istniejącego panelu DNS; przegląd obecnych rekordów |
| Poczta | Nazwa usługi, host SMTP, port 465 lub 587, właściwy tryb TLS, login i dozwolony nadawca |
| Wysyłka aplikacyjna | Zgoda dostawcy na ten rodzaj wysyłki, limity i zasady blokad |
| Uwierzytelnienie domeny | Rekordy SPF i DKIM wskazane przez dostawcę oraz plan DMARC |

Hasła, klucze SSH, tokeny panelu i klucze szyfrujące wprowadzać prywatnie
na właściwym urządzeniu; nie umieszczać ich w repozytorium ani w rozmowie.
Dokładne rekordy DNS zależą od dostawcy. Zachować obecne rekordy przed zmianą,
nie tworzyć drugiego rekordu SPF ani nie nadpisywać istniejącej poczty w ciemno.

## Kolejność podłączenia

1. Uruchomić prywatny podgląd według URUCHOMIENIE_PODGLADU_NA_SERWERZE.md:
   osobne konto systemowe, lokalna baza, ograniczona rola, klucz poza repozytorium,
   API dostępne przez tunel SSH. Nie wystawiać portów 8000 ani 5432 publicznie.
2. Sprawdzić rejestrację, logowanie, katalog, uprawnienia i trwałość po restarcie.
   Rzeczywiste płatności pozostają odłączone.
3. Skonfigurować skrzynkę i parametry SMTP oraz istniejącą domenę zgodnie
   z instrukcją wybranego dostawcy. Skrzynka obsługi i automatyczne powiadomienia
   mogą mieć różne konfiguracje; nie zakładać wspólnych limitów.
4. Sprawdzić lokalną konfigurację poczty poniższym narzędziem. Następnie osobno
   wykonać kontrolowaną próbę połączenia i dostarczenia do własnej skrzynki.
   Narzędzie nie łączy adaptera SMTP z HTTP ani nie uruchamia pracownika.
5. Przed uruchomieniem okresowego pracownika przygotować jego oddzielną rolę,
   konto/usługę i nadzorcę. Nadal wymagany jest odbiór kopii, odtworzenia oraz
   procedury DB + klucze; istniejące próby CI nie zastępują odbioru na VPS.
6. Publiczne HTTPS, podłączenie domeny do aplikacji i prawdziwi użytkownicy
   wymagają osobnego odbioru. Nie usuwać blokady WP_ENV=production samą zmianą
   zmiennej. Pierwszy podgląd można sprawdzić bez zmieniania publicznego DNS.

## Lokalna kontrola konfiguracji poczty

Uruchomić jako docelowy użytkownik usługi, z prywatnie przekazaną konfiguracją:

```sh
python -m scripts.check_mail_configuration
```

Kontrola używa istniejących walidatorów. Nie tworzy ani nie zmienia plików,
nie odpytuje DNS, nie otwiera połączenia SMTP i nie uruchamia kolejki.
Nie włącza żadnej flagi konfiguracji. Raport zawiera wyłącznie stałe statusy.

| Pole | Znaczenie |
| --- | --- |
| smtp | VALID, DISABLED lub REJECTED: lokalna konfiguracja adaptera SMTP |
| queue_keys | VALID, DISABLED lub REJECTED: plik kluczy kolejki |
| ready_for_connection_test | Obie powyższe konfiguracje przeszły walidację |
| network_checked | Zawsze false; host, port i certyfikat nie zostały sprawdzone w sieci |
| delivery_checked | Zawsze false; nie potwierdzono dostarczenia wiadomości |

Kod wyjścia 0 oznacza wyłącznie gotowość lokalnej konfiguracji do następnego
testu, a 1 — co najmniej jeden komponent wyłączony lub odrzucony.
VALID nie potwierdza poprawności hasła u dostawcy, uprawnień nadawcy,
dostarczalności, SPF/DKIM/DMARC ani działania całej aplikacji.
Pliki sekretów wymagają POSIX, praw prywatnych i ścieżek poza repozytorium.
Na Windows ten test nie zastępuje walidacji na docelowym Linuxie.

## Co już sprawdzono

Kod kwarantanny 30de9b8: pełny Linux 4050 PASS / 0 FAIL / 68 SKIP,
pełny Windows 3972 PASS / 0 FAIL / 146 SKIP; PostgreSQL 44/44,
Chromium 36/36 wraz z HTTP w pięciu rozmiarach, szybki Windows 80/80.
Dowody: audits/restore_quarantine_30de9b8_2026-10-19/.
Wyników pokrywających się pakietów nie sumować. Późniejsze zmiany runnera
i narzędzie kontroli konfiguracji wymagają własnego odbioru.
