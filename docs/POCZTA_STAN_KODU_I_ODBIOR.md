# Poczta — stan kodu i odbiór po zakupie

Sprawdzenie źródeł: 18.10.2026. Nie podłączono dostawcy poczty i nie wysłano
wiadomości z aplikacji. Zakup skrzynki nie uruchamia automatycznie
powiadomień ani odzyskiwania hasła.

## Co już istnieje

| Element | Faktyczny stan |
| --- | --- |
| Adres przy rejestracji i logowaniu | Zapis adresu i uwierzytelnienie hasłem; nie jest dowodem własności skrzynki |
| Polityka kanałów | backend/notification_policy.py dopuszcza e-mail i panel; odrzuca SMS i telefon |
| PIN odbioru | Polityka dopuszcza wyłącznie panel; nie wysyłać go pocztą |
| Reset hasła w demo | Losowy token, hash w bazie, 15 minut, jednorazowość, limity, cofnięcie sesji |
| Dostarczenie resetu | Prywatny plik JSON w lokalnym demo SQLite; brak SMTP |
| Reset na PostgreSQL | Domyślnie wyłączony; osobny opt-in prywatnego testu lokalnego, opis RESET_HASLA_POSTGRESQL_TESTOWY.md; bez SMTP |
| Powiadomienia o zakupie/dostawie | Istnieje polityka kanałów; nie ma podłączonej wysyłki ani kolejki SMTP |
| Weryfikacja e-maila | Wymieniona w polityce zdarzeń; nie stanowi wdrożonego przepływu potwierdzenia adresu |

Źródła audytu: backend/app.py (RESET_TEST_ENABLED i trasy password-reset-test),
backend/password_reset.py, backend/notification_policy.py.
Wyników demo nie przypisywać rzeczywistej poczcie ani PostgreSQL.

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

1. Wprowadzić jawnie włączany transport z TLS, bez haseł w kodzie i logach;
   brak konfiguracji ma pozostawić funkcję wyłączoną.
2. Zaimplementować potwierdzanie adresu i przechowywanie stanu weryfikacji.
   Powiadomienia transakcyjne muszą respektować istniejącą politykę kanałów.
3. Odebrać testowy protokół resetu PostgreSQL opisany w
   RESET_HASLA_POSTGRESQL_TESTOWY.md i dostosować go do właściwego transportu.
   Sam SMTP nie zastępuje kolejki, zasad odbiorców i odbioru całego procesu.
4. Oddzielić wysyłkę od żądania HTTP: kolejka, kontrolowane ponowienia,
   spójność stanu i limit wysyłek. Nie wysyłać losowych kodów do nieznanych
   adresów jak w prywatnej skrzynce demo; odpowiedź HTTP nadal ma być ogólna.
5. Przygotować link na ustalonym adresie HTTPS, bez przyjmowania hosta
   z dowolnego nagłówka żądania; nie utrwalać tokenu w logach i analityce.
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
