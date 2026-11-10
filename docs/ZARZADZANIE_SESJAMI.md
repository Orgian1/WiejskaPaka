# Zarządzanie sesjami w wersji testowej

Panel bezpieczeństwa konta zawiera trzy działania dla każdej roli:

- „Sprawdź sesje”: liczba aktualnie ważnych logowań tego konta i pozostałych
  sesji. Kilka logowań z jednej przeglądarki to kilka sesji, nie kilka urządzeń.
- „Wyloguj pozostałe sesje”: usuwa wszystkie inne tokeny tego konta,
  także wygasłe; bieżący token pozostaje aktywny.
- „Wyloguj wszystkie sesje”: cofa również token użyty do tej operacji.

API: `GET /auth/sessions`, `POST /auth/logout-others`, istniejące
`POST /auth/logout` i `POST /auth/logout-all`. Wszystkie wymagają Bearer.
Podgląd zwraca wyłącznie `active_sessions`, `other_sessions`,
`current_expires_at` (UTC). Nie zwraca tokenów, ich skrótów, e-maila, adresów,
telefonów, IP ani identyfikatorów przeglądarek. Odpowiedzi mają `no-store`.
Podgląd nie usuwa danych; nieprawidłowe i wygasłe daty nie zwiększają licznika.

Wylogowanie bieżącej sesji usuwa dane widoku od razu. Jeśli sieć zawiedzie lub
serwer zwróci błąd, komunikat wyraźnie informuje, że cofnięcie tokenu na serwerze
nie zostało potwierdzone. Odpowiedź 401 oznacza, że token jest już nieważny.
Komunikat starego żądania nie nadpisuje widoku nowego zalogowanego konta.

## Transakcje i współbieżność

W SQLite blokada `BEGIN IMMEDIATE` poprzedza ponowne sprawdzenie tokenu,
terminu ważności i roli. W PostgreSQL używana jest ta sama transakcyjna blokada
po e-mailu co przy logowaniu i zmianie hasła. Po jej uzyskaniu API ponownie
sprawdza aktualną sesję w tej samej transakcji. Kod PostgreSQL ma test opt-in;
wykonanie na prawdziwym serwerze pozostaje bramką odbioru, dopóki środowisko
nie umożliwi jego uruchomienia.

Dwa urządzenia równocześnie wylogowujące pozostałe sesje nie mogą oba
potwierdzić sukcesu: pierwszy zapis cofa token drugiego, drugi otrzymuje 401.
Wycofanie transakcji przy błędzie bazy zachowuje tokeny. Wspólny mechanizm
stosowany jest też przy zmianie hasła.

Cofnięcie sesji nie zmienia hasła. Nowe logowanie poprawnym hasłem po operacji
jest dozwolone; także logowanie współbieżne może zostać zatwierdzone po
wylogowaniu. Przy podejrzeniu poznania hasła przez inną osobę należy je zmienić
— wtedy stare hasło przestaje działać, a wszystkie wcześniejsze sesje są cofane.
Operacje autoryzowane i rozpoczęte wcześniej nie są automatycznie anulowane.
Danych już wyświetlonych na innym urządzeniu nie można zdalnie wymazać.

## Granice funkcji

Nie ma listy nazw urządzeń ani cofania wybranego urządzenia; aplikacja nie
zbiera takich danych. Liczniki pokazują stan z chwili odczytu i mogą się zmienić
po kolejnym logowaniu. Nie zapisujemy ich w pamięci trwałej przeglądarki.
Utrata odpowiedzi na operację oznacza nieznany wynik: można bezpiecznie
sprawdzić sesje ponownie. Cofnięcie nie narusza zakupów, szyfrogramów PIN,
kluczy, terminów rezerwacji, magazynu ani rozliczeń.

Odzyskanie zapomnianego hasła pozostaje niewdrożone. Ten pakiet nie podłącza
usług e-mail/SMS ani produkcyjnych płatności.

## Czyszczenie danych widoku

Każda zmiana konta i wylogowanie od razu usuwa stare karty katalogu, zamówień,
koszyka, punktów, panelu i powiadomień. Czyści też adres wpisany w koszyku,
wybór sprzedawcy i punktu, sumę, e-mail formularza logowania oraz szkice
produktów, profilu i punktu. Nie czeka na odpowiedź sieci, więc czyszczenie działa
również offline. Wartości kontrolek i teksty usuwanych węzłów są zerowane przed
odłączeniem ich od DOM. Nie jest to obietnica wymazania wszystkich kopii danych
z pamięci przeglądarki ani treści już pobranych na innym urządzeniu.
