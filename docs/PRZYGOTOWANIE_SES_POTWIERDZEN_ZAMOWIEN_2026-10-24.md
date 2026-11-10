# Przygotowanie potwierdzeń zakupów przez SES

Przygotowano warstwę wiadomości i trwały rejestr prób. Nie włączono samoczynnej wysyłki ani nie podłączono danych dostępowych AWS. Kod HTTP zakupów nie wywołuje nowej kolejki; nie uruchomiono usługi lub procesu pocztowego na VPS.

## Treść wiadomości

`backend/order_mail.py` tworzy polską wiadomość tekstową z numerem pojedynczego zamówienia albo wspólnej paczki, produktami i zapisanymi jednostkami, sumą produktów, jedną opłatą dostawy, sumą końcową, terminem rezerwacji i sześciocyfrowym PIN-em. Kwoty są formatowane z całkowitej liczby groszy, bez obliczeń na float. Wiadomość wskazuje wprost rezerwację testową i brak rzeczywistej płatności. Aktualny status oraz decyzję sprzedawcy klient sprawdza po zalogowaniu.

Źródłem treści są niezmienne zapisy zakupu i istniejący zaszyfrowany sejf checkout. Nie odtwarza się cen lub nazw z bieżącej oferty. Numer telefonu i pełny adres klienta nie są dodawane do wiadomości. PIN, pozycje i identyfikator wiadomości są ukryte w reprezentacji obiektu używanej do diagnostyki. Temat nie zawiera PIN-u.

Zmiana polityki powiadomień dopuszcza PIN przez e-mail wyłącznie po potwierdzeniu własności adresu klienta. Dla niezweryfikowanego adresu pozostaje panel. Builder i adapter wymagają dokładnej wartości `True`; publiczna flaga przesłana przez klienta nie może być źródłem tej decyzji.

## Transport SMTP

Wspólna funkcja `submit_message` w dotychczasowym module SMTP obsługuje TLS przed uwierzytelnieniem i jednego odbiorcę w kopercie. Dodatkowe To/Cc/Bcc są odrzucane. Reset hasła zachowuje dotychczasowy interfejs.

Przyjęcie przez SMTP to `ACCEPTED`, nie dowód trafienia do skrzynki. Zerwanie połączenia podczas DATA to wynik niepewny. Błąd zamykania po potwierdzonym przyjęciu nie zmienia go w nieudaną wysyłkę. Adapter nie ponawia operacji i nie wypisuje treści, PIN-ów ani danych dostępowych.

`load_ses_config` jest domyślnie wyłączony. Po świadomym włączeniu sprawdza zgodność regionu z hostem SMTP i domeny nadawcy. Hasło SMTP jest czytane z prywatnego pliku poza repozytorium przez istniejącą kontrolę uprawnień POSIX.

Szablon `deploy/preview/ses-orders.env.example` odpowiada regionowi użytemu w konfiguracji domeny: `eu-north-1`, host `email-smtp.eu-north-1.amazonaws.com`, STARTTLS na porcie 587, nadawca `noreply@wiejskapaka.pl`. To dane przygotowawcze, nie konfiguracja zainstalowana na VPS. Wartość `WP_ENABLE_ORDER_SMTP=0` pozostaje domyślna. Potrzebne są dane **SMTP SES** właściwego regionu, a nie hasło konsoli AWS. Oficjalne źródła: [endpointy SES](https://docs.aws.amazon.com/general/latest/gr/ses.html), [dane SMTP SES](https://docs.aws.amazon.com/ses/latest/dg/smtp-credentials.html).

## Trwały rejestr prób

`backend/order_mail_outbox.py` oraz opcjonalna migracja `database/optional_order_mail_outbox.sql` definiują rejestr powiązany kluczem obcym z zapisanym checkout. Unikalność `(buyer_id, request_key)` zapobiega tworzeniu drugiego zadania dla ponowionego zakupu. Uwzględniono przestrzeń nazw `direct:` używaną przez istniejące zakupy bezpośrednie.

Rejestr nie przechowuje adresu e-mail wprost, treści ani kopii PIN-u. Zawiera identyfikatory zakupu, skrót adresu oraz stan. Zmiana adresu, anulowanie, wygaśnięcie rezerwacji, brak potwierdzenia własności adresu lub uszkodzenie sejfu blokuje wysyłkę.

Wywołanie `enqueue` wymaga transakcji. Docelowy kod zakupów powinien wywołać je wewnątrz tej samej transakcji co zapis checkout. `dispatch_once` wymaga jawnie dostarczonych: połączenia, sejfu, transportu, zegara i funkcji sprawdzającej zweryfikowany adres. Funkcja weryfikacji musi odczytywać zaufany stan potwierdzenia adresu dla bieżącego użytkownika. Samo zweryfikowanie domeny w SES nie potwierdza adresów klientów. Testowe funkcje zwracające zawsze `True` nie są implementacją produkcyjną.

Przed zewnętrznym wywołaniem zapisywany i zatwierdzany jest stan `started`. Drugie wykonanie lub równoległy proces nie otrzymuje tego samego zadania. Przerwane próby stają się `uncertain`; nie wracają automatycznie do kolejki. Nawet jednoznaczne odrzucenie pozostaje końcowym stanem tej próby i wymaga osobnej, audytowanej decyzji operatora. Nie deklaruje się gwarancji jednokrotnego dostarczenia do skrzynki.

Odtwarzanie SQLite i PostgreSQL obejmuje blokowanie historycznego rejestru: oczekujące zadania są pomijane, a rozpoczęte pozostają niepewne. Nie zmienia to kolejki w źródłowej bazie. Migrację dodano do manifestu i blokady sum kontrolnych oraz szablonu przygotowania nowej testowej bazy; nie zastosowano jej do VPS.

Kontrola przed startem wymaga `order_mail_outbox`, jeśli ustawiono `WP_ENABLE_ORDER_SMTP=1`. Nie tworzy tabeli i nie włącza samoczynnej wysyłki.

## Następne kroki przed włączeniem

1. Dokończyć potwierdzanie własności adresu e-mail w aplikacji i podłączyć autorytatywną kontrolę odbiorcy.
2. Wpiąć rejestr w transakcje obu ścieżek checkout oraz uruchamiany jawnie, ograniczony proces wysyłający z bezpiecznym raportowaniem błędów.
3. Potwierdzić status domeny i MAIL FROM w SES oraz dostęp do wysyłki w wybranym regionie. W sandboxie testować na zweryfikowanym odbiorcy.
4. Prywatnie umieścić dane SMTP na serwerze; wykonać kontrolowaną testową wysyłkę i sprawdzić nagłówki, treść oraz odbiór.
5. Przed wysyłką do klientów podłączyć obsługę odbić i skarg oraz limity tempa wysyłki. Sama akceptacja SMTP nie wystarcza do monitorowania dostarczenia.

Do zakończenia tych kroków kod pozostaje przygotowaniem integracji, a nie aktywnym automatycznym wysyłaniem potwierdzeń.

## Walidacja

Lokalne testy obejmują TLS, ochronę nagłówków, pojedynczego odbiorcę, politykę zweryfikowanego adresu, deduplikację wpisów, dwa równoległe procesy, utratę odpowiedzi, trwały zapis przed SMTP, restart po rozpoczęciu, wygaśnięcie, zmianę adresu i oferty, oba checkout oraz rzeczywiste odtworzenie kopii SQLite. Wszystkie używają syntetycznych danych i wstrzykniętego transportu; nie wysyłają e-maili.

Dodano trzy scenariusze natywnego PostgreSQL: przyjęcie, niepewny wynik i niezweryfikowany odbiorca. Ich wynik wymaga wykonania osobnego zadania CI PostgreSQL 16 i 17; lokalne testy SQLite nie są dowodem wykonania PostgreSQL.

Lokalny izolowany przebieg końcowy: **168 PASS, 0 FAIL, 0 SKIP, 12/12 modułów**, źródła niezmienione podczas wykonania. Dowód bez treści wiadomości i sekretów: `docs/audits/ses_order_mail_2026-10-24/local-summary.json`. Kontrola manifestu i sum kontrolnych migracji oraz `git diff --check`: PASS. Nie wykonano rzeczywistego połączenia SMTP ani wysyłki do SES.
