# Zmiana hasła i cofnięcie sesji

Po zalogowaniu sekcja **Bezpieczeństwo konta** pozwala zmienić hasło. Wymaga
obecnego hasła, nowego hasła i powtórzenia nowego hasła. Nowe hasło ma 12–256
znaków i musi różnić się od obecnego. Nie przycinamy spacji ani znaków Unicode.
Osobny przepływ odzyskiwania zapomnianego hasła w lokalnym demo opisuje
`ODZYSKIWANIE_HASLA_TESTOWE.md`; rzeczywista wysyłka nadal nie jest podłączona.

`POST /auth/change-password` przyjmuje wyłącznie `current_password` oraz
`new_password`. Sesja oraz aktualna rola są ponownie sprawdzane w transakcji.
Działa dla istniejących kont klienta, rolnika, dostawcy i administratora;
nie tworzy nowych kont administracyjnych. Nie przyjmuje ID konta w żądaniu.

Nowe hasło jest haszowane Argon2id. Aktualizacja skrótu i usunięcie **wszystkich**
sesji konta, w tym bieżącej, następują atomowo. Inne konta zachowują sesje.
Po sukcesie interfejs czyści token, hasła, PIN i dane zalogowanego konta,
a następnie wymaga ponownego logowania. Cofnięcie tokenu blokuje kolejne
żądania także z innych urządzeń; nie usuwa zdalnie treści wcześniej wyświetlonej
na ich ekranach. Nie ma tu zewnętrznego kanału powiadomień.

## Równoległość i ograniczenie prób

SQLite używa `BEGIN IMMEDIATE`. PostgreSQL używa tej samej blokady doradczej
adresu konta co logowanie. Po uzyskaniu blokady jeszcze raz sprawdzana jest
sesja: druga równoczesna zmiana nie może użyć tokenu już cofniętego przez pierwszą.
Logowanie starym hasłem albo kończy się przed usunięciem sesji i jego token
jest usuwany, albo po zmianie widzi nowy skrót i otrzymuje odmowę. Brama
natywnego PostgreSQL musi niezależnie potwierdzić ten scenariusz na serwerze.

Limit wynosi 5 prób na konto w 15 minut, niezależnie od tokenu. Błędne hasło
zwraca 401 bez cofania dotychczasowych sesji, ale próba zostaje zapisana.
Kolejna próba po wykorzystaniu limitu daje 429 z `Retry-After`. Restart nie
zeruje licznika. To osobne okno od logowania i odzyskiwania PIN-u. Zmiana hasła
nie resetuje licznika PIN-u, prób odbioru, kluczy szyfrowania ani retencji.

Awaria haszowania lub usuwania sesji wycofuje całość. Hasła nie trafiają do
odpowiedzi walidacji ani komunikatów błędów. Odpowiedzi mają `no-store`.
Pola formularza są czyszczone przed wysłaniem żądania; nie zapisujemy haseł
ani tokenu w pamięci trwałej przeglądarki. Spóźniona odpowiedź z poprzedniej
sesji nie wylogowuje konta zalogowanego później. Po utracie odpowiedzi należy
sprawdzić logowanie nowym hasłem — wynik mógł już zostać zapisany.

## Migracja

SQLite tworzy `password_change_access` automatycznie. PostgreSQL wymaga
ręcznego zastosowania `database/upgrade_z_password_change.sql` na odizolowanej
bazie testowej; brak tabeli blokuje start nowej aplikacji. Tabela zawiera tylko
ID konta, liczbę prób i początek okna. Nie zawiera haseł ani tokenów.
Przed aktualizacją własnej instalacji zachowaj spójną kopię bazy i osobny klucz.
Nie uruchamiamy żadnych migracji na Neon ani usługach produkcyjnych.

Pola hasła logowania i rejestracji są także czyszczone przed żądaniem, również
przy późniejszej odmowie. Zmiana konta lub wylogowanie czyści pole logowania.
Po rejestracji hasło trzeba podać ponownie lub użyć własnego menedżera haseł.
