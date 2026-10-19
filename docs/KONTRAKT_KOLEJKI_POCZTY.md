# Kontrakt kolejki poczty — projekt następnego etapu

Kontrakt z 18.10.2026. Część SQLite zaimplementowano 19.10.2026 w osobnym,
odłączonym module; zakres opisuje KOLEJKA_RESETU_SQLITE.md. Ten dokument
nadal obejmuje wymagania docelowe, w tym niewykonane etapy integracji.
Nie jest migracją, włącznikiem wysyłki ani dowodem dostarczenia.
Punkty odniesienia: backend/password_reset.py, backend/notification_policy.py,
backend/smtp_reset_transport.py i trasy password-reset-test w backend/app.py.

## Granica między panelem i wysyłką

Obecna tabela notifications ma obowiązkowe order_id i służy panelowi.
Nie używać jej jako kolejki resetu hasła ani przechowywać tam tokenu.
Kolejka transportowa musi być oddzielna od widocznych powiadomień użytkownika.

Testowe issue() zwraca losowy token także dla nieznanego adresu. Docelowa
operacja musi wewnętrznie rozróżnić istniejące konto i utworzyć zadanie tylko
dla adresu pobranego z tego konta. Nie przekazywać do SMTP samego adresu
z żądania. Odpowiedź HTTP pozostaje ogólna dla adresu znanego, nieznanego,
objętego limitem i niedostępnej poczty. Status dostawcy pozostaje wewnętrzny.

Polityka dopuszcza reset i weryfikację adresu przed oznaczeniem go jako
zweryfikowanego; pozostałe zdarzenia e-mail wymagają potwierdzenia adresu.
Nie zmieniać tej różnicy przypadkowo: użytkownik ma móc dowieść kontroli nad
skrzynką przez link, a zgłoszenie resetu nie dowodzi jeszcze jej własności.
PIN odbioru pozostaje dostępny wyłącznie w panelu.

## Atomowość i sekrety

Wydanie hasha tokenu, zużycie limitu i utworzenie zadania muszą zostać
zatwierdzone w tej samej transakcji. Awaria po commit nie może zgubić zadania;
rollback nie może pozostawić zadania zdolnego do wysyłki. Wywołanie SMTP
następuje po zakończeniu transakcji, nigdy pod blokadą konta.

Do wysłania potrzebny jest oryginalny token, choć tabela resetu przechowuje
wyłącznie jego hash. Kolejka potrzebuje więc szyfrowanego ładunku, osobnego
klucza i identyfikatora jego wersji; nie umieszczać jawnego tokenu w bazie,
logach, błędzie API, raporcie CI ani panelu administratora. Szyfrowanie musi
uwierzytelniać powiązanie z identyfikatorem zadania, typem zdarzenia i kontem.
Nie wykorzystywać klucza sejfu zamówień lub hasła SMTP jako klucza kolejki.
Odtworzenie kopii musi uwzględnić potrzebne wersje klucza i ryzyko ponownej
wysyłki historycznych zadań; sam restore nie może uruchamiać pracownika.

Ładunek usuwać po wyniku terminalnym lub wygaśnięciu. Dalszy audyt może
zachować identyfikator, czasy, liczbę prób i ustalony kod wyniku, bez tokenu
lub surowej odpowiedzi dostawcy. Retencję danych odbiorcy określić jawnie.

## Stany i przejmowanie zadań

| Stan | Znaczenie | Dalsze działanie |
| --- | --- | --- |
| queued | Zadanie zatwierdzone, oczekuje na próbę | Przejęcie przez jednego pracownika |
| leased | Czasowa dzierżawa z identyfikatorem właściciela | Tylko właściciel może zapisać wynik |
| accepted | SMTP potwierdził przyjęcie | Bez ponawiania; nie oznacza dostarczenia |
| uncertain | Brak pewnego wyniku po rozpoczęciu przekazania | Bez automatycznego ponowienia |
| failed | Trwała odmowa lub wyczerpane próby | Bez ponawiania, bez sekretów w audycie |
| expired | Link wygasł lub został unieważniony | Bez wysyłki |

Jawna przejściowa odmowa może wrócić do queued z terminem następnej próby.
Liczba prób i odstępy muszą być ograniczone; termin nie może przekraczać
ważności linku. Sprawdzić ważność i wersję hasła przed próbą, a nie tylko
podczas tworzenia zadania. Pracownik nie wydaje nowego linku samodzielnie.

Na PostgreSQL pobieranie oczekujących zadań wymaga atomowego przejęcia
(np. blokady wierszy z SKIP LOCKED i zapisu dzierżawy w krótkiej transakcji).
Wariant SQLite potrzebuje jawnej serializacji zapisów. Nie wykonywać SMTP
w transakcji utrzymującej te blokady. Zapisy wyniku muszą sprawdzać właściciela
i wersję dzierżawy, żeby spóźniony pracownik nie nadpisał nowszego wyniku.

Utrata procesu po przyjęciu wiadomości, ale przed zapisem accepted, jest
niejednoznaczna. Sam upływ dzierżawy nie upoważnia do powtórzenia wysyłki.
Potrzebny jest trwały znacznik rozpoczęcia próby; osierocona próba po tej
granicy trafia do uncertain, dopóki nie ma bezpiecznego dowodu jej wyniku.
Nie deklarować dokładnie jednokrotnego dostarczenia przez zwykłe SMTP.

## Integracja i odbiór bez dostawcy

Przed podłączeniem usług zewnętrznych kolejne testy powinny potwierdzić:

- wspólny commit i rollback tokenu, limitów oraz zadania, także po wymuszonej awarii;
- brak zadania dla nieznanego konta i ogólną odpowiedź HTTP;
- jednego właściciela zadania przy dwóch pracownikach i odporność na spóźniony zapis;
- wznowienie po restarcie oraz rozróżnienie awarii przed i po rozpoczęciu próby;
- brak ponowienia accepted/uncertain, ograniczone próby po jawnej odmowie przejściowej;
- wygasanie i unieważnianie po zmianie hasła, usunięcie szyfrowanego ładunku;
- odmowę pracy przy złym kluczu, uszkodzonym ładunku i nieznanej wersji klucza;
- brak tokenu i danych uwierzytelnienia w logach, odpowiedziach oraz artefaktach;
- zgodność typów zdarzeń z polityką kanałów i zakaz wysyłania PIN-u;
- domyślne wyłączenie pracownika i brak wywołania sieci bez jawnej konfiguracji.

Odbiór DNS, certyfikatu serwera SMTP i dostarczeń wymaga potem osobnego testu
u wybranego dostawcy na kontrolowanych skrzynkach. Lokalne zastąpienie SMTP
nie może być przedstawione jako dowód tych właściwości.
