# Wspólny limit wysyłki weryfikacji i potwierdzeń zakupów

## Zmiana

Obie jawne komendy SES wymagają teraz WP_MAIL_MIN_INTERVAL_SECONDS i
WP_MAIL_DAILY_LIMIT. Nie ma domyślnych limitów przypisywanych kontu Amazon.
Wartości trzeba dobrać do potwierdzonej konfiguracji konta przed prawdziwym testem.
Brak/błędne wartości blokują wysyłkę jeszcze przed odczytaniem sekretów.
Bez --send komendy nadal niczego nie czytają ani nie wysyłają.

`backend/mail_send_budget.py` utrzymuje jeden wspólny budżet w bazie aplikacji.
Weryfikacja adresu i potwierdzenia zakupów nie mają oddzielnych pul. Pierwsza
próba zapisuje politykę; różne ustawienia kolejnych procesów są odrzucane.
Zmiana polityki wymaga osobnej kontroli offline, nie następuje automatycznie.

## Koordynacja

Roszczenie do wysyłki i znacznik rozpoczęcia wiadomości zapisują się w tej samej
transakcji. SQLite używa BEGIN IMMEDIATE, PostgreSQL blokady transakcyjnej.
Tylko jeden proces może zajmować wspólną dzierżawę. SMTP pracuje po zatwierdzeniu
transakcji, a po jego zakończeniu wynik kolejki i zwolnienie dzierżawy zapisują
się razem. Odstęp liczony jest od zakończenia próby, zaokrąglonego w górę do
pełnej sekundy; ułamki sekund nie pozwalają na wcześniejszy start następnej.

Dzierżawa po awarii trwa 120 sekund, dłużej niż maksymalne 60 sekund pracy
procesu plus czas jego wymuszonego zakończenia. Nie jest to pozwolenie na
ponowienie rozpoczętej wiadomości. Jej los nadal określa trwały rejestr kolejki.
Stary właściciel nie może zwolnić dzierżawy przejętej przez nowy proces.

Dziennik prób z indeksem czasu egzekwuje limit z ostatnich 24 godzin, bez
wyzerowania całego licznika na granicy okna. Czas próby jest konserwatywnie
przesuwany na koniec operacji lub koniec osieroconej dzierżawy. Odrzucenie,
awaria połączenia i niepewny wynik również zużywają limit. Dziennik nie zawiera
adresów, PIN-ów, treści wiadomości ani identyfikatorów klientów.

Przy zajętej dzierżawie lub wyczerpanym limicie zwracane jest RATE_LIMITED.
Wiadomość pozostaje queued, jej sekret nie jest kasowany, nie powstaje próba SMTP.
Partia kończy się bez oczekiwania w pętli; uruchomienie kolejnej partii musi
zapewnić późniejszy harmonogram. Domyślna komenda nadal nie uruchamia demona.

## Migracja i kopie

Nowa ręczna migracja optional_mail_send_budget.sql tworzy mail_send_budget
oraz mail_send_attempts. Dodano ją do przeglądanego manifestu i szablonu nowej
bazy. Preflight obu komend wymaga obu tabel. DDL nie jest wykonywany przez proces.

Odtworzenie kopii SQLite/PostgreSQL ustawia paused=1, zachowuje historię prób
i nie wznawia wysyłki automatycznie. Dotyczy również pustego budżetu. Kopia nie
wie, ile oryginalna baza wysłała od momentu jej utworzenia; nie wolno uznać jej
licznika za aktualną dostępność konta SES. Źródłowa baza pozostaje bez zmian.

## Weryfikacja

Lokalnie 217 zaliczonych testów, 0 błędów, 0 pominięć, 19 izolowanych modułów,
niezmienione źródła. Wśród scenariuszy: równoległe połączenia, proces spawn, dwie kolejki naraz,
odstęp ułamkowej sekundy, prawdziwy limit kroczący, awaria i stare zwolnienie,
rollback, rozbieżna konfiguracja, zatrzymanie procesu przy limicie, zachowanie
sekretu odłożonej wiadomości oraz faktyczne odtworzenie kopii.

Dodano natywny wyścig o budżet PostgreSQL i włączono rzeczywistą bramkę limitów
w istniejących testach procesów obu typów. Ich wyniki wymagają bieżącego CI.
Poprzedni pakiet przeszedł PostgreSQL 16/17, Chromium i szybki Windows; pełny
Windows przy sprawdzaniu pozostawał w toku. Nie są to wyniki tej zmiany.

## Zakres i dalsze kroki

Limit obejmuje dwie komendy SES korzystające z JEDNEJ wspólnej bazy. Nie obejmuje
innych baz ani zewnętrznych nadawców tego samego konta Amazon. Prywatne funkcje
biblioteczne nadal mogą być jawnie wywoływane z transportem zastępczym bez polityki;
nie są automatycznymi ścieżkami wysyłki. Przed inną rzeczywistą integracją SMTP
należy objąć ją tą samą bramką. Duże przeskoki zegara systemowego wymagają kontroli.

Sprawdzono obsługę natychmiastowego REJECTED i DELIVERY_UNCERTAIN: brak ponowienia
i brak zwrotu zużytej przepustowości. NIE dodano jeszcze odbioru ani uwierzytelniania
zewnętrznych powiadomień SES o późniejszym odbiciu/skardze, listy wykluczeń czy
monitorowania operacyjnego. To osobny etap przed publicznym uruchomieniem.
Pozostają także rzeczywisty test SMTP i skrzynki oraz konfiguracja harmonogramu.
Nie wysłano wiadomości do SES i nie zmieniono VPS.
