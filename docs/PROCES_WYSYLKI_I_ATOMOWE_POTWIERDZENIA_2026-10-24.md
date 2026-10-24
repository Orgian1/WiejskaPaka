# Ograniczony proces wysyłki i atomowy zapis potwierdzeń

## Zachowanie

`python -m scripts.send_verification_batch` bez `--send` zwraca DISABLED,
nie czyta kluczy ani haseł i nie łączy się z bazą czy SMTP.

Jawne `--send --max-jobs 3 --timeout-seconds 30` uruchamia skończoną partię
w osobnym procesie. Dozwolone są 1–25 zadań i 1–60 sekund. Przekroczenie czasu
kończy proces; raport zawiera wyłącznie stały status i liczniki, nigdy adres,
link, hasło ani DSN. Niepewny wynik nie jest podstawą ponownej wysyłki.
Wspólna granica procesu została rozszerzona o jawny dispatcher, a dotychczasowe
zachowanie kolejki resetowania hasła pozostaje domyślne i jest osobno testowane.

Komenda obsługuje wyłącznie PostgreSQL środowiska testowego, sprawdza docelową
bazę, nieuprzywilejowaną rolę i obecność schematu w procesie objętym limitem.
Nie importuje aplikacji, nie tworzy tabel, nie migruje i nie uruchamia demona.
Wyjątki konfiguracji/sterowników są zastępowane stałym WORKER_FAILED.

## Konfiguracja przed przyszłym testem wysyłki

Komenda wymaga jawnego włączenia `WP_ENABLE_EMAIL_VERIFICATION=1`,
`WP_ENABLE_VERIFICATION_SMTP=1` i `WP_ENABLE_MAIL_QUEUE=1`, prywatnego pliku kluczy
kolejki oraz ustawień SES i prywatnego pliku hasła SMTP z szablonu
`deploy/preview/ses-orders.env.example`. Hasło SMTP nie jest hasłem konsoli AWS.
Ustawienia bazy pochodzą z zatwierdzanej konfiguracji testowego serwera
(`WP_ENV=test`, `WP_TEST_DATABASE_URL`); odziedziczone zmienne zmieniające routing
libpq są odrzucane. Sekrety pozostają poza repozytorium.

Włączenie wysyłki weryfikacji nie włącza wysyłki zakupów. Komenda nie wprowadza
harmonogramu ani koordynacji limitów konta SES; przed prawdziwą próbą trzeba
sprawdzić jego region, tryb konta i limit. Pierwszy test należy ograniczyć do
jednej wiadomości i własnej skrzynki. Nie wysłano żadnej wiadomości do SES.

## Powiązanie z zakupem

Osobna flaga `WP_ENABLE_ORDER_MAIL_QUEUE=1` włącza zapis potwierdzeń w obu
ścieżkach: pojedynczy produkt i koszyk. Wymaga modułu weryfikacji adresów.
Dla potwierdzonego adresu zamówienie, rezerwacja, oryginalne warunki zakupu,
zaszyfrowana odpowiedź idempotencyjna i wpis kolejki są jedną transakcją.
Awaria zapisu wiadomości wycofuje cały zakup i zmianę magazynu, a koszyk pozostaje.
Powtórzenie tego samego zakupu zwraca wcześniejszą odpowiedź bez drugiej wiadomości.

Dla niepotwierdzonego adresu zakup nadal działa w panelu, ale wiadomość nie trafia
do kolejki. Takich wcześniejszych zakupów nie dopisuje się automatycznie po
późniejszym potwierdzeniu adresu. Dispatcher ponownie sprawdza własność adresu,
aktualność zamówienia i PIN-u. Potwierdzenia nadal opisują rezerwację TESTOWĄ,
bez pobrania rzeczywistej płatności. Dostawa pozostaje jedną opłatą za przesyłkę.
Żądania HTTP nie łączą się z SMTP.

## Weryfikacja

Lokalnie: 174 testy zaliczone, 0 błędów, 0 pominiętych, 14 izolowanych modułów.
Obejmują procesy spawn, limit partii/czasu, brak wycieku wyjścia adaptera,
nieponawianie niepewnej próby, konfigurację CLI, oba checkouty, rollback zakupu
przy błędzie kolejki oraz połączenie checkout → kolejka → zaufany callback
weryfikacji → odtworzenie danych zakupu → zastępczy transport.

Dodano testy natywne PostgreSQL: ograniczony proces wraz z preflightem oraz oba
checkouty z ponowieniem i wymuszoną awarią kolejki. Ich wynik będzie oceniany
w CI dla tego commitu, oddzielnie od lokalnego wyniku.

Zachowano raporty POPRZEDNIEJ wersji 70e9584, przebieg 40115616026:
PostgreSQL 16 i 17 po 59/59, Chromium 50/50 oraz testy rozmiarów ekranu.
Nie stanowią wyniku nowej zmiany. Pełny Windows tej wersji był nadal w toku
przy sprawdzaniu; nie deklarujemy zakończenia całej regresji.

## Pozostaje

Proces wysyłający wiadomości o zakupach (obecna komenda wysyła weryfikację),
rzeczywisty test SES i odbioru wiadomości, limity/monitorowanie odrzuceń i skarg,
konfiguracja uruchamiania procesu i wdrożenie po kopii bezpieczeństwa.
VPS nie był modyfikowany. Wszystkie nowe flagi są domyślnie wyłączone.
