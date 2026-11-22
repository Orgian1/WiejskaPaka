# WiejskaPaka — regulamin i prywatność demo

Projekt do podglądu przed publikacją. Pola w nawiasach kwadratowych wymagają uzupełnienia zgodnie z faktyczną konfiguracją serwera.

## Regulamin wersji demonstracyjnej

### Prowadzący i kontakt

Demo WiejskaPaka (wiejskapaka.pl) prowadzi Marek Liczner, [adres prowadzącego]. Pytania, zgłoszenia techniczne i reklamacje dotyczące działania demo można wysłać na marek.liczner@gmail.com. W zgłoszeniu opisz problem i wskaż, kiedy wystąpił. Odpowiedź otrzymasz na adres, z którego wyślesz wiadomość.

### Do czego służy demo

Demo pozwala obejrzeć oferty, przetestować konto kupującego lub sprzedawcy i poznać przebieg zamówienia, odbioru oraz operacji portfela. Wymaga przeglądarki obsługującej JavaScript i dostępu do internetu. Za korzystanie z demo nie pobieramy opłat. Produkty, ceny, zamówienia, PIN-y, salda i wypłaty służą do symulacji. Zamówienie testowe nie skutkuje sprzedażą ani dostawą. W serwisie można zobaczyć przykładowe reklamy dla kupujących i sprzedawców.

### Konto i dane testowe

Konto jest potrzebne do przetestowania funkcji przypisanych do wybranej roli. W formularzach demo używaj danych fikcyjnych lub danych testowych otrzymanych od prowadzącego. Użyj hasła przeznaczonego wyłącznie do tego demo. Oferty, zdjęcia, opisy i informacje o punktach odbioru mogą być widoczne dla innych osób. Wstawiaj wyłącznie materiały, które możesz udostępnić. Nie umieszczaj cudzych danych osobowych ani treści bezprawnych.

Korzystanie z demo możesz zakończyć w każdej chwili. Jeśli chcesz usunąć konto testowe, napisz na adres kontaktowy. Dane testowe mogą zostać usunięte przy porządkowaniu lub zakończeniu demo zgodnie z zasadami wskazanymi w informacji o prywatności.

## Informacja o prywatności i pamięci przeglądarki

### Administrator, cele i dane

Administratorem danych przetwarzanych przy obsłudze demo jest Marek Liczner, [adres prowadzącego], kontakt: marek.liczner@gmail.com.

| Cel | Dane | Podstawa przewidziana dla demo |
| --- | --- | --- |
| Prowadzenie konta i udostępnianie funkcji testowych | Adres użyty do założenia konta, rola, identyfikator, skrót hasła, wpisy zapisane w panelu i historia czynności testowych | Art. 6 ust. 1 lit. b RODO w zakresie niezbędnym do świadczenia usługi |
| Zabezpieczenie kont i serwisu oraz diagnozowanie błędów | Dane techniczne połączeń i zdarzenia związane z działaniem aplikacji, w zakresie wynikającym z konfiguracji logów | Art. 6 ust. 1 lit. f RODO, interes polegający na ochronie serwisu i kont |
| Kontakt i rozpatrywanie zgłoszeń | Adres e-mail, treść wiadomości i odpowiedzi | Art. 6 ust. 1 lit. f RODO, interes polegający na obsłudze zgłoszeń, a w sprawach realizacji usługi art. 6 ust. 1 lit. b RODO |

Adres wpisywany przy rejestracji i hasło są potrzebne do utworzenia konta. Przekazanie danych kontaktowych jest dobrowolne, a adres e-mail umożliwia udzielenie odpowiedzi.

### Lokalizacja i mapy

Przeglądarka pyta o dostęp do GPS po uruchomieniu odpowiedniej funkcji. Funkcja „Blisko mnie” używa położenia do wyszukiwania ofert. Sprzedawca może użyć GPS do wyboru położenia punktu albo do potwierdzenia obecności przy punkcie. Potwierdzenie korzysta ze współrzędnych i dokładności pomiaru. Zapisany adres i położenie punktu mogą być publiczne. Uprawnienie GPS można zmienić w ustawieniach przeglądarki.

Po wybraniu szczegółowej mapy ulic przeglądarka pobiera obrazy mapy z OpenStreetMap. Żądania ujawniają dostawcy adres IP i obszar odpowiadający wyświetlonym kafelkom. Mapa poglądowa jest dostępna w aplikacji.

### Dostawcy, przechowywanie i prawa

Dostawcą hostingu jest netcup GmbH. Dostawcę poczty, rolę ewentualnego pośrednika sieciowego, lokalizacje przetwarzania i informacje o ewentualnym przekazywaniu danych poza EOG należy uzupełnić na podstawie konfiguracji [dostawcy i lokalizacje]. Oferty oraz publiczne informacje o punktach mogą odczytywać odwiedzający demo.

Przed publikacją trzeba ustalić i wdrożyć terminy lub kryteria usuwania danych kont i czynności testowych, logów, kopii zapasowych oraz korespondencji [zasady przechowywania].

W sprawie dostępu do danych, ich sprostowania, usunięcia, ograniczenia przetwarzania, przeniesienia lub sprzeciwu możesz napisać na podany adres e-mail. Prawa przysługują na zasadach określonych w RODO. Możesz też złożyć skargę do Prezesa Urzędu Ochrony Danych Osobowych.

### Pamięć przeglądarki

Aplikacja używa pamięci karty przeglądarki (sessionStorage), aby bezpiecznie ponowić rozpoczęte zamówienie lub testową operację portfela po przerwaniu połączenia. Zapis zawiera dane techniczne potrzebne do rozpoznania operacji. Token logowania działa w pamięci otwartej strony.

Po włączeniu dokumentów w konfiguracji demo licznik pierwszych pięciu logowań jest zapisany na koncie. Przeglądarka nie zapisuje wówczas licznika instrukcji w pamięci trwałej. Informację należy uzupełnić po sprawdzeniu cookies na publicznej domenie.

## Przed udostępnieniem

- Uzupełnić adres prowadzącego, datę obowiązywania oraz zasady retencji. Sprawdzić podstawy przetwarzania dla opcjonalnych funkcji lokalizacji i map.
- Zweryfikować na VPS dostawców, konfigurację kopii i logów oraz działanie poczty. Sprawdzić nagłówki i pamięć przeglądarki na publicznej domenie przed zalogowaniem i w obu panelach.
- Zastosować `database/upgrade_demo_login_guide.sql` na PostgreSQL po próbie na kopii. Uzupełnić w konfiguracji demo `WP_DEMO_OPERATOR_ADDRESS`, `WP_DEMO_LEGAL_DATE`, `WP_DEMO_DATA_RETENTION` i `WP_DEMO_DATA_PROVIDERS`. Aplikacja wtedy wyświetli linki przy rejestracji i w stopce.

Podstawa prawna: [ustawa o świadczeniu usług drogą elektroniczną, art. 5 i 8](https://eli.gov.pl/api/acts/DU/2024/1513/text.html), [Prawo komunikacji elektronicznej, art. 399](https://eli.gov.pl/eli/DU/2024/1221/ogl), [RODO, art. 6 i 13](https://eur-lex.europa.eu/legal-content/PL/TXT/?uri=CELEX:32016R0679).
