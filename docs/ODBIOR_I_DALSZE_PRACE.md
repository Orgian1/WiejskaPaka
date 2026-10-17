# Odbiór wersji testowej i następne prace

Stan po paczce zarządzania sesjami z 16 października 2026. To lista warunków
odbioru, nie deklaracja wykonania ani zgoda na produkcyjne integracje.
Aktualne liczby uruchomionych testów znajdują się w `RAPORT_SESJE_2026-10-16.md`.

| Obszar | Obecny stan | Warunek dalszego odbioru |
| --- | --- | --- |
| PostgreSQL | Adapter, migracje i testy opt-in; natywna bramka niewykonana | Jednorazowy lokalny serwer pod nieuprzywilejowaną tożsamością, izolowana baza, ograniczona rola aplikacji; pełny zestaw natywny bez SKIP, w tym sesje, wyścigi, zakup i zwrot |
| Chromium i telefon | Rzeczywisty HTTP, Node z kontrolowanym DOM i kontrola znaczników; bez potwierdzonego odbioru przeglądarkowego | Uruchomienie rzeczywistej przeglądarki; odbiór każdej roli na wąskim ekranie, klawiaturą, z utratą sieci i przełączeniem konta |
| Zapomniane hasło | Zmiana hasła wymaga starego; odzyskanie niewdrożone | Zatwierdzony kanał kontaktu, krótkotrwały losowy token trzymany w postaci skrótu, jednorazowe użycie, limit prób, ochrona przed ujawnianiem istnienia konta i cofnięcie sesji po zmianie; brak resetu samym e-mailem lub ID |
| Utrata PIN-u | Odzyskanie istniejącego kodu po haśle do 24 godzin; bez resetu blokady | Bezpieczny kanał produkcyjny i procedura po upływie retencji, bez drugiego zakupu i bez obchodzenia licznika prób odbioru |
| Weryfikacja sprzedawcy | Testowe potwierdzenie zasad i przegląd administracyjny; bez danych identyfikacyjnych i prawdziwych wypłat | Ustalony cel i podstawa przetwarzania, bezpieczny operator, minimalny zakres, retencja i kontrola dostępu; bez wpisywania prawdziwych danych do demo |
| Próg uzupełnienia profilu | Nie jest ustanowionym przez aplikację progiem prawnym | Rozdzielić regułę produktu, np. przypomnienie po 20 transakcjach, od wymagań prawnych; ustalić co jest ukończoną transakcją i jak traktować zwroty |
| Płatności i wypłaty | Wyłącznie symulacje; grosze, idempotencja, pełny zwrot i historia | Uzgodniony operator i model opłat, weryfikacja zdarzeń i uzgodnienie sald; integracji produkcyjnej nie uruchamiać w obecnym zadaniu |
| Dostawcy i punkty | Opłata za adres naliczana raz w przesyłce; odbiór w punkcie | Uzgodnić wynagrodzenia i odpowiedzialność stron; nie wyprowadzać ich z samej testowej funkcji podziału 75/20/5 |
| Prawa konsumenta | Informacja o zachowaniu ustawowych praw; PIN potwierdza odbiór | Niezależna ocena docelowych regulaminów, informacji i procesów obsługi; nie utożsamiać testowego anulowania z kompletną procedurą konsumencką |
| Dane i kopie | Szyfrowany cache PIN; adresy lokalnej bazy nadal jawne | Docelowa ochrona całej bazy, kluczy, kopii i logów; odtworzenie oraz usuwanie danych zgodnie z przyjętą retencją |

## Co można teraz sprawdzić lokalnie

Uruchomić jednorazowe demo według README, tworzyć wyłącznie syntetyczne konta,
produkty i zakupy. Potwierdzić dodatnią opłatę przy dostawie na adres, odbiór
w punkcie, jedną opłatę za przesyłkę, sprawdzenie towaru przed PIN-em, blokadę
kodu po błędnych próbach oraz testowy pełny zwrot z dostawą przy winie dostawcy.

W panelu konta sprawdzić liczbę sesji po dwóch logowaniach, wylogować pozostałe,
sprawdzić odrzucenie starego tokenu i zachowanie bieżącego. Następnie zmienić
hasło i potwierdzić odrzucenie wszystkich wcześniejszych tokenów. Zmiana hasła
nie powinna zmieniać zamówień, klucza szyfrowania ani budżetu odzyskiwania PIN-u.

Powtórzone uruchomienia należy liczyć oddzielnie od odrębnych przypadków testów.
Nie nadawać statusu PASS zadaniu, które nie zostało uruchomione, nie uznawać
kontroli źródeł za wykonanie w przeglądarce i nie przenosić wyników SQLite na
PostgreSQL. Wynik testu śmierci procesu nie jest certyfikatem odporności na
awarię dysku lub utratę zasilania.

## Ograniczenia pracy autonomicznej

Kontynuować lokalnie bez GitHub, Actions, usług płatnych i połączeń produkcyjnych.
Nie podłączać Neon, płatności, domeny ani hostingu. Nie publikować kodu, danych,
baz ani kluczy. W ZIP przekazywać kod, testy i dowody; robocze dane oraz klucz
pozostawić poza archiwum. Nie zbierać ani nie udostępniać telefonów użytkowników.
