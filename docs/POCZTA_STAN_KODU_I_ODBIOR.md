# Poczta — stan kodu i odbiór po zakupie

Sprawdzenie źródeł: 19.10.2026. Nie podłączono dostawcy poczty i nie wysłano
wiadomości z aplikacji. Zakup skrzynki nie uruchamia automatycznie
powiadomień ani odzyskiwania hasła.

## Co już istnieje

| Element | Faktyczny stan |
| --- | --- |
| Adres przy rejestracji i logowaniu | Zapis adresu i uwierzytelnienie hasłem; nie jest dowodem własności skrzynki |
| Polityka kanałów | backend/notification_policy.py dopuszcza e-mail i panel; odrzuca SMS i telefon |
| PIN odbioru | Polityka dopuszcza wyłącznie panel; nie wysyłać go pocztą |
| Reset hasła w demo | Losowy token, hash w bazie, 15 minut, jednorazowość, limity, cofnięcie sesji |
| Dostarczenie resetu | Prywatny plik JSON lub testowa zaszyfrowana kolejka po pełnym opt-in; adapter SMTP nie jest wywoływany z HTTP |
| Reset na PostgreSQL | Domyślnie wyłączony; osobny opt-in prywatnego testu lokalnego, opis RESET_HASLA_POSTGRESQL_TESTOWY.md; bez SMTP |
| Powiadomienia o zakupie/dostawie | Istnieje polityka kanałów; nie ma podłączonej wysyłki ani kolejki SMTP |
| Weryfikacja e-maila | Wymieniona w polityce zdarzeń; nie stanowi wdrożonego przepływu potwierdzenia adresu |

Źródła audytu: backend/app.py (RESET_TEST_ENABLED i trasy password-reset-test),
backend/password_reset.py, backend/notification_policy.py.
Wyniki SQLite i PostgreSQL mają oddzielne raporty; żadnego z nich nie
przypisywać rzeczywistej poczcie.

## Dane potrzebne od dostawcy

- Skrzynka kontaktowa w domenie i wybrany adres nadawcy wiadomości aplikacji.
- Możliwość wysyłki transakcyjnej, limity, zasady blokad i obsługa zwrotów.
- Host, port i wymagany tryb TLS; dane logowania wprowadzone prywatnie.
- Wartości DNS do SPF, DKIM i DMARC oraz wskazanie istniejących rekordów,
  aby nie zastąpić konfiguracji innej aktywnej poczty.
- Dostęp do logów dostarczeń i błędów bez udostępniania treści tokenów.

Nie trzeba kupować osobnej domeny, jeśli wykorzystujemy już posiadaną
wiejskapaka.pl. Konfigurację DNS sprawdzić w aktualnym panelu przed zmianą.
Nie zmieniać rekordów ani nie wysyłać testów do cudzych adresów automatycznie.

## Prace programistyczne przed uruchomieniem poczty

1. Połączyć przygotowany adapter TLS z autoryzowanym wyborem odbiorcy
   i kolejką. Adapter jest już jawnie włączany i domyślnie wyłączony;
   jego lokalne testy nie potwierdzają działania u dostawcy.
2. Zaimplementować potwierdzanie adresu i przechowywanie stanu weryfikacji.
   Powiadomienia transakcyjne muszą respektować istniejącą politykę kanałów.
3. Dostosować przetestowany protokół resetu PostgreSQL opisany w
   RESET_HASLA_POSTGRESQL_TESTOWY.md do właściwego transportu.
   Sam SMTP nie zastępuje kolejki, zasad odbiorców i odbioru całego procesu.
4. Oddzielić wysyłkę od żądania HTTP: kolejka, kontrolowane ponowienia,
   spójność stanu i limit wysyłek. Nie wysyłać losowych kodów do nieznanych
   adresów jak w prywatnej skrzynce demo; odpowiedź HTTP nadal ma być ogólna.
5. Zachować ustalony adres HTTPS linku z adaptera podczas integracji
   z aplikacją, bez przyjmowania hosta z dowolnego nagłówka żądania;
   nie utrwalać tokenu w logach i analityce.
6. Zapewnić ogólny komunikat przy odmowie dostawcy, błędzie TLS, limicie
   i przerwie w dostępności; brak wycieku istnienia konta lub sekretów.

## Odbiór po konfiguracji

Użyć własnych kont testowych i skrzynek kontrolowanych przez operatora.
Potwierdzić dostarczenie, nadawcę i wyniki SPF/DKIM/DMARC, wygaśnięcie
linku, jednorazowość i cofnięcie sesji po resecie. Sprawdzić próby równoległe,
ponowienie po awarii dostawcy, limit i brak podwójnego zdarzenia użytkownika.
Nie dopuszczać wysyłki PIN-u ani numerów telefonów.

Do czasu wykonania tych prac podgląd PostgreSQL może służyć testom z
syntetycznymi kontami, ale nie ma działającego odzyskiwania zapomnianego
hasła przez e-mail. Tę różnicę trzeba zachować w komunikacji o gotowości.

Adapter i jego ograniczenia opisuje ADAPTER_SMTP_PRZYGOTOWANIE.md; wyniki
bieżącego pakietu zawiera RAPORT_POCZTY_PRZYGOTOWANIE_2026-10-18.md.


## Kolejny etap — 19.10.2026

`KOLEJKA_RESETU_SQLITE.md` opisuje osobny moduł szyfrowanej kolejki SQLite.
Nie jest podłączony do HTTP lub SMTP i nie ma procesu w tle.
`RAPORT_KOLEJKI_POCZTY_2026-10-19.md` rozdziela jego testy od dotychczasowej
bramki PostgreSQL. Integracja aplikacji, PostgreSQL, zarządzanie kluczami,
retencja i potwierdzenie adresów pozostają osobnym zakresem.


## Wykonanie PostgreSQL i klucze — kolejny pakiet 19.10.2026

`KOLEJKA_RESETU_POSTGRESQL.md` opisuje odłączone wykonywanie na PgConnection,
a `KLUCZE_KOLEJKI_POCZTY.md` jawny odczyt prywatnego pliku wersjonowanych
kluczy. Moduły pozostają poza trasami HTTP i bez procesu w tle.
Integracja aplikacji, potwierdzanie adresów, retencja, kopie kluczy i odbiór
u dostawcy pozostają dalszym zakresem. Aktualne dowody zawiera
`RAPORT_KOLEJKI_POSTGRESQL_I_KLUCZY_2026-10-19.md`.


## Prywatny przepływ HTTP kolejki — kolejny pakiet 19.10.2026

`RESET_HASLA_KOLEJKA_HTTP_TEST.md` opisuje jawne połączenie żądania resetu
z szyfrowaną kolejką i ogólną odpowiedzią 202 także po błędzie zapisu.
`RAPORT_RESETU_HTTP_KOLEJKI_2026-10-19.md` zawiera aktualne dowody.
Nie ma automatycznej wysyłki: kolejka testowa jest wykonywana ręcznie
z transportem w pamięci. Pracownik, potwierdzanie adresów, retencja,
kopie kluczy i odbiór dostawcy wymagają dalszych prac.
