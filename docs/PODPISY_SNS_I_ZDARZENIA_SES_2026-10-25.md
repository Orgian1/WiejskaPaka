# Podpisy SNS i transakcyjne zdarzenia SES — prywatny moduł

## Implementacja

`sns_pinned_notification.verify` przyjmuje surowy dokument i jawnie zaufaną
konfigurację Pin. Akceptuje tylko Notification, SignatureVersion2 i podpis
RSA/SHA256, właściwą kolejność podpisywanych pól z opcjonalnym Subject oraz
końcowym znakiem nowej linii. Weryfikuje dokładny temat ARN, adres certyfikatu,
UUID i datę. Dokument ma maksymalnie 128 KiB; niejednoznaczne klucze JSON,
niestandardowe stałe, nieprawidłowe typy i przekroczone limity są odrzucane.

Certyfikat jest przypięty przez operatora poza otrzymanym dokumentem. Sprawdzane
są typ/rozmiar RSA i ważność certyfikatu w chwili podpisu oraz odbioru. Kod nie
pobiera certyfikatów z sieci, nie podąża za SubscribeURL i nie potwierdza subskrypcji.
Domyślna świeżość wynosi 24 godziny, dopuszczalne wyprzedzenie 60 sekund;
operator może ustawić okno od godziny do 7 dni. Starsze zgłoszenia wymagają
kontrolowanej obsługi, nie powinny być bez śladu porzucane przez przyszły odbiornik.

## Granica zaufania

Pin jest JAWNĄ kotwicą zaufania dostarczaną przez operatora. Sam moduł nie
zatwierdza łańcucha CA dowolnego PEM i nie udowadnia pochodzenia certyfikatu
pobranego z nieznanego źródła. Pin/temat nie mogą pochodzić z parametrów żądania.
Brakuje jeszcze bezpiecznego dostarczania i rotacji rzeczywistych certyfikatów.
Samopodpisane certyfikaty w testach są syntetycznymi pinami, nie dowodem zaufania AWS.

Podpis SNS potwierdza pochodzenie z tematu, lecz nie dowodzi, jaki podmiot mógł
opublikować jego treść. Przed uruchomieniem trzeba ograniczyć uprawnienia
publikacji tematu do zamierzonego konta/tożsamości SES. Konfiguracja SignatureVersion2
również musi odpowiadać tematowi. Nie aktywowano żadnego endpointu HTTP ani importera.

## Transakcja SES

`ses_feedback.apply` ZAWSZE ponownie weryfikuje surowe zgłoszenie; nie akceptuje
flagi verified=true ani gotowego obiektu Notification jako autoryzacji zapisu.
Następnie wymaga zgodnej tożsamości SES, regionu i konta. Jednoznaczne trwałe
odbicie albo skarga abuse jednego odbiorcy może zapisać blokadę. Odbiorca musi
odpowiadać jednemu adresowi z oryginalnego destination. Wpis blokady i dziennika
zdarzeń należą do tej samej transakcji. Awaria dziennika wycofuje również blokadę.

Duplikat tego samego zdarzenia i treści zwraca DUPLICATE. Inna treść przy tym samym
identyfikatorze powoduje błąd, bez nadpisania. PostgreSQL serializuje identyfikator
zdarzenia blokadą transakcyjną. W bazie przechowywane są tylko skróty identyfikatora
oraz treści, stały wynik i czas odbioru, bez adresów i surowego dokumentu.

Przejściowe odbicia, Delivery i not-spam nie odblokowują adresu. Brak/ukrycie
adresu, wiele adresów i nieobsługiwane typy trafiają do REVIEW, bez zgadywania
odbiorcy. Przyszły odbiornik musi zachować takie zgłoszenie w prywatnej kolejce
lub archiwum do kontroli; sam dziennik skrótów nie wystarczy do odtworzenia treści.
Nie dodano jeszcze mapowania identyfikatorów SES do odbiorców.

## Regresja Windows i audyty

Przebieg poprzednika 40119699868, commit 660fbf2: 4336 zaliczonych, 3 błędy,
200 pominiętych; szybki zestaw Windows 80/80. Wszystkie trzy błędy odtworzono:
- inwentarz tras nie znał publicznego GET /auth/email-verification/options;
- drugi audyt korzystał z tej samej nieaktualnej klasyfikacji;
- ścisła lista skryptów nie uwzględniała dodanego email-verification.js.

Dodano dokładny wyjątek metody/ścieżki wyłącznie dla informacji o dostępności.
Status konta, żądanie i potwierdzenie nadal wymagają current_user. Test sprawdza
wszystkie trzy zależności oraz brak szerszego wyjątku. Lista skryptów zachowuje
pełną kolejność i wymaganie defer; dopisano do niej właściwy moduł.

Aktualny pakiet: 99/99 lokalnych testów, 0 błędów i pominięć w 13 izolowanych
modułach, niezmienione źródła. Audyt rzeczywistego anonimowego HTTP: 107/107 tras
niepublicznych zablokowanych, bez wyników niejednoznacznych. To nie jest wynik
pełnej regresji Windows. Dodano natywny wyścig PostgreSQL dla identycznego
podpisanego zdarzenia; bieżące CI musi go jeszcze wykonać.

## Dalsze kroki

Kontrolowana konfiguracja/rotacja pinów, bezpieczny odbiornik i archiwum zdarzeń,
polityka publikacji tematu, obsługa starej kolejki i retencji, korelacja messageId,
monitorowanie, rzeczywisty test własnej skrzynki i dopiero wdrożenie z kopią.
Nie wysłano wiadomości do SES i nie zmieniono VPS.

Źródła protokołu:
- https://docs.aws.amazon.com/sns/latest/dg/sns-verify-signature-of-message-verify-message-signature.html
- https://docs.aws.amazon.com/sns/latest/dg/sns-verify-signature-of-message.html
- https://docs.aws.amazon.com/ses/latest/dg/notification-contents.html
