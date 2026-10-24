# Proces wysyłki potwierdzeń zakupów i PIN-ów

## Zakres

Dodano `backend/order_mail_worker.py` i komendę:

```
python -m scripts.send_order_confirmation_batch
```

Domyślnie wynik to DISABLED. Nie są wtedy czytane sekrety ani otwierane połączenia.
Jawne `--send --max-jobs 1 --timeout-seconds 30` może wykonać jedną partię po
poprawnej konfiguracji. Limity procesu są wspólne z kolejką weryfikacji/resetu:
1–25 zadań, 1–60 sekund, zakończenie procesu przy przekroczeniu czasu, stały
raport zawierający wyłącznie status i liczniki. Brak automatycznych ponowień.

Wspólna walidacja połączenia została wydzielona z komendy weryfikacji. Lista
wymaganych tabel preflightu może być dobrana przez zaufany kod; dla zakupów są
to account_email_proofs oraz order_mail_outbox, oprócz schematu podstawowego.

## Dane i zabezpieczenia

Proces korzysta z istniejącego sejfu odpowiedzi zakupowych. Wczytuje jawnie
wskazany, istniejący plik WP_CHECKOUT_KEY_FILE poza repozytorium, tylko na POSIX,
z kontrolą właściciela, uprawnień i braku dowiązania. Nie tworzy klucza zastępczego.
Nie zapisuje dodatkowej kopii PIN-u w kolejce ani raporcie. Własność adresu
ponownie potwierdza callback odczytujący rzeczywisty rejestr konta, bez flagi
przekazanej przez klienta i bez utożsamiania tego z potwierdzeniem domeny SES.

Zasady wspólne z istniejącym dispatcherem:
- odtworzenie oryginalnej nazwy, jednostki, ilości, kwot i jednej dostawy za paczkę;
- pominięcie niepotwierdzonego/zmienionego adresu oraz anulowanej lub wygasłej rezerwacji;
- trwały znacznik rozpoczęcia przed połączeniem SMTP;
- przyjęcie przez SMTP oznacza jedynie przyjęcie przez serwer;
- awaria lub niepewna odpowiedź nie powoduje ponownej wysyłki;
- sekret oraz dane odbiorcy nie przechodzą przez raport procesu.

## Flagi i konfiguracja

Wywołanie wysyłające wymaga WP_ENV=test, prywatnej konfiguracji testowego
PostgreSQL i nieuprzywilejowanej roli oraz trzech oddzielnych flag:
WP_ENABLE_ORDER_MAIL_QUEUE=1, WP_ENABLE_EMAIL_VERIFICATION=1, WP_ENABLE_ORDER_SMTP=1.
Dane SES i zewnętrzny plik hasła SMTP pochodzą z dotychczasowego szablonu.
Wysyłka zakupów nie włącza wysyłki weryfikacji i odwrotnie. Nie zainstalowano
harmonogramu ani demona. Samo zaimportowanie kodu niczego nie wysyła.

Wiadomości opisują aktualną rezerwację TESTOWĄ, nie potwierdzenie prawdziwej
płatności. Przed podłączeniem operatora należy osobno powiązać komunikację
płatniczą z autorytatywnym wynikiem płatności.

## Testy

Lokalnie 130 testów w 10 izolowanych modułach: 0 błędów i 0 pominięć, niezmienione
źródła aplikacji między oboma przebiegami. Testy obejmują proces spawn,
nieponawianie przyjętej/niepewnej wysyłki, ograniczenie czasu, brak wycieku wyjścia,
kwalifikację odbiorcy, prywatny istniejący klucz, konfigurację obu komend i regresję
wspólnej granicy procesu resetowania hasła.

Dodano natywne testy PostgreSQL: rzeczywisty zakup i rejestr potwierdzenia adresu,
proces spawn z preflightem, brak drugiej wysyłki i odmowa po cofnięciu dowodu
własności. Transport jest zastąpiony, bez SES. Wyniki tych testów wymagają CI.

## Diagnoza starszego błędu Windows

Przebieg 40114375030 (commit 4f7c030, PR #28) miał jeden błąd:
test_package5.py:10, audyt wydania oczekujący braku luk schematu. W tym commicie
tabela account_email_proofs była zdefiniowana w backendzie, lecz nie miała jeszcze
migracji PostgreSQL. Kolejny PR #29 dodał optional_email_verification.sql.

Aktualny audit_schema zwraca missing_in_postgres=[], a wszystkie 4 testy modułu
test_package5.py przeszły. To diagnoza starego przebiegu, nie deklaracja zaliczenia
obecnej pełnej regresji Windows. Przebieg wcześniejszego PR #27 (40113687370)
zakończył cały Windows sukcesem; kolejne wersje mają oddzielne wyniki.

## Pozostaje przed uruchomieniem

Test z rzeczywistymi danymi SMTP i własną skrzynką, koordynacja limitów konta SES,
monitorowanie odrzuceń/skarg, konfiguracja uruchamiania partii na serwerze,
wdrożenie po kopii bezpieczeństwa i testy całego procesu na VPS. Domyślny limit
jednej wiadomości ułatwia pierwszą próbę, ale nie stanowi globalnego ogranicznika
wysyłki przy równoległym uruchamianiu wielu procesów. Niczego nie wysłano do SES
ani nie zmieniono na VPS.
