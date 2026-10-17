# WiejskaPaka — zarządzanie sesjami i odporność na przerwanie procesu

Data: 16 października 2026. Commit kodu i testów: `1fb4fef05634d08ad8b2b4f7bde4c721937e6bf0`.
Odcisk kodu aplikacji, skryptów, SQL i zadeklarowanych zależności: `ad069b1c651f77c8b61546aa05f9fb7af1935c6d79d998bef58763f023962558`.

## Wynik paczki

Dodano prywatny podgląd liczby sesji, wylogowanie pozostałych sesji oraz panel
obsługi sesji dla klienta, rolnika, dostawcy i administratora. Naprawiono
ponowną autoryzację wylogowania w SQLite oraz mylący komunikat po błędzie sieci.

Pełna regresja: **3317 PASS, 0 FAIL, 19 SKIP**, 260 modułów i 3336 zebranych
przypadków. W tym **67 nowych zaliczonych przypadków**. Nowy natywny test
PostgreSQL ma SKIP. Wyniki SKIP nie oznaczają zaliczenia.

Prace, lokalne commity i archiwizacja bez GitHub, publikacji, Actions,
produkcyjnych płatności, hostingu, domeny, Neon ani usług płatnych.
Nie podajemy niepotwierdzonego procentu ukończenia ani liczby wykonanych
zadań na podstawie oznaczenia B/10921–B/11280.

## Naprawione problemy i funkcje

1. **Ponowna autoryzacja wylogowania.** Wcześniej lokalne wylogowanie mogło
   opierać się wyłącznie na wcześniejszym odczycie sesji w zależności FastAPI.
   Teraz cofnięty lub wygasły token oraz zmieniona rola są ponownie sprawdzane
   w transakcji, po uzyskaniu blokady. Dotyczy wylogowania bieżącej sesji,
   wszystkich sesji, pozostałych sesji i ich podglądu.
2. **Wylogowanie pozostałych sesji.** Nowe `POST /auth/logout-others` zachowuje
   wyłącznie token użyty do operacji, usuwa inne tokeny tego konta i nie narusza
   sesji innych użytkowników. Powtórzenie jest bezpieczne. Dwa urządzenia
   wylogowujące się wzajemnie mają jednego zwycięzcę; drugi token otrzymuje 401.
3. **Prywatny podgląd.** `GET /auth/sessions` pokazuje liczby aktywnych logowań
   i termin ważności bieżącego tokenu w UTC. Nie ujawnia tokenów, ich skrótów,
   e-maila, telefonów, IP ani danych urządzeń. Wygasłe, niepoprawne i pozbawione
   strefy daty nie są liczone. Podgląd nie usuwa rekordów. Wygaśnięcie pomiędzy
   autoryzacją a odczytem daje 401 zamiast 500.
4. **Komunikat po wylogowaniu offline.** Widok i token lokalny są czyszczone
   od razu. Błąd sieci albo serwera pokazuje brak potwierdzenia cofnięcia na
   serwerze. Odpowiedź 401 oznacza już nieważny token. Odpowiedź wcześniejszego
   żądania nie nadpisuje komunikatu na później zalogowanym koncie.
5. **Wspólna blokada bezpieczeństwa konta.** SQLite używa `BEGIN IMMEDIATE`;
   PostgreSQL używa tej samej blokady doradczej po e-mailu co logowanie i zmiana
   hasła, a potem ponownie odczytuje token. Ścieżka PostgreSQL wymaga wykonania
   natywnego testu. Nie zmieniano schematu bazy w tej paczce.
6. **Interfejs.** Panel oferuje sprawdzenie sesji, wylogowanie pozostałych oraz
   wszystkich. Blokuje podwójne kliknięcia i odrzuca spóźnione odpowiedzi po
   zmianie konta, wylogowaniu lub nowszym żądaniu. Używa tekstu, bez wstawiania
   HTML i bez zapisywania danych sesji w pamięci trwałej przeglądarki.
7. **Odporność na nagłe przerwanie procesu.** Sześć nowych przypadków naprawdę
   zabijają własny proces Uvicorn podczas lub po żądaniu zakupu i zwrotu,
   restartują go i ponawiają operacje. Obejmują pojedynczy zakup, koszyk,
   utratę odpowiedzi, zaszyfrowany cache PIN, opłatę dostawy tylko raz, dokładnie
   jeden zwrot, brak podwójnej wypłaty oraz integralność SQLite i kluczy obcych.
   Sprawdzają także atomowość zmiany hasła i cofnięcia wszystkich tokenów
   podczas przerwania oraz po odebranej odpowiedzi. To próba śmierci procesu,
   nie symulacja awarii zasilania ani test PostgreSQL.

8. **Pozostawiony adres i stare karty przy zmianie konta.** Usunięto pozostawianie
   wpisanego adresu dostawy i prywatnych widoków do czasu odpowiedzi sieci.
   Czyszczenie następuje natychmiast, również offline i przy bezpośrednim
   przejściu na inne konto. Czyści pola i teksty także w odłączanych węzłach.

## Wykonane testy

| Kontrola | Wynik |
| --- | --- |
| Pełna regresja w osobnych procesach i jednorazowych bazach | 3317 PASS, 0 FAIL, 19 SKIP; źródła niezmienione |
| Nowe testy: API sesji / prawdziwy HTTP / JS sesji / komunikat wylogowania / nagłe przerwanie procesu | 33 / 3 / 11 / 7 / 6 PASS; osobno 7 PASS czyszczenia prywatnych widoków |
| Długotrwały HTTP | 1500.35 s, 11309 rund, 106188 żądań, 263870 kontroli |
| Zmiana hasła kontra stare logowanie w długim HTTP | 113 wyścigów |
| Dwa urządzenia cofające sesje w długim HTTP | 113 wyścigów |
| Odzyskanie PIN w długim HTTP | 2262 żądań, 10 sukcesów, 2252 ograniczonych |
| Cofnięte/wygasłe tokeny: 88 tras × 4 role × 5 scenariuszy | 1760 żądań, 3520 sprawdzeń kodu 401 i no-store; 0 błędów |
| Anonimowy dostęp do prywatnych tras | 88/88 zablokowanych; 0 niejednoznacznych |
| Zakupy i historia przez rzeczywisty TCP HTTP | 50 żądań, 187 sprawdzeń, PASS |
| Pakiet akceptacji HTTP | 4/4 zadania PASS |
| Rozliczenia w groszach vs niezależny wzorzec Decimal | 20 001 kwot, 100 002 sprawdzenia, PASS |
| Składnia i zależności | 374 plików Python, 13 JS; pip check PASS |

Skrypty HTTP używają prawdziwego serwera na loopback i tymczasowego SQLite.
Pełną regresję po nowych próbach awarii wykonano z czystej kopii. Końcowy zestaw
zawiera wszystkie nowe testy, w tym rozszerzone próby przerwania procesu oraz
czyszczenie prywatnych widoków. Po ostatniej poprawie wykonano ponownie cały zestaw. Nie sumujemy powtórzeń, żądań HTTP ani kontroli
własności z liczbą odrębnych przypadków pytest.

Pierwsza pełna regresja wykazała trzy niezgodne wcześniejsze testy: stara
makieta połączenia nie zwracała sesji do dodatkowej autoryzacji, a dwa kontrakty
źródłowe oczekiwały poprzedniej konstrukcji funkcji. Zaktualizowano makietę oraz
sprawdzanie kolejności blokady, autoryzacji i czyszczenia sesji. Nie wyłączono
zabezpieczeń. Jedno pośrednie uruchomienie przerwano przed poprawą tych testów;
nie jest przedstawiane jako zaliczone. Po poprawie czyszczenia widoków uaktualniono także stary kontrakt resetowania formularzy.
Wcześniejszy długi test HTTP zatrzymano po zmianie kodu i nie uznano go za zaliczony.
Końcowy pełny wynik i nowy nieprzerwany test HTTP są powyżej.

## Zasady zakupów i granice bezpieczeństwa

Wykonane testy nadal obejmują dostawę na adres za dodatnią opłatą, bezpłatny
odbiór w punkcie, dostawę naliczaną raz dla przesyłki, odbiór z PIN-em oraz
100% zwrotu z dostawą przy winie dostawcy. Kwoty i rozliczenia pozostają
całkowitymi groszami. PIN nie pozbawia konsumenta ustawowych praw. Nie zbieramy
ani nie udostępniamy numerów telefonów. Test podziału 75/20/5 potwierdza rachunek,
nie zatwierdza tej zasady jako produkcyjnej polityki lub podstawy prawnej.

Wylogowanie nie zmienia hasła. Kolejne poprawne logowanie, również zatwierdzone
po współbieżnym wylogowaniu, jest możliwe. Przy podejrzeniu przejęcia hasła trzeba
je zmienić; zmiana hasła cofa wszystkie wcześniejsze tokeny. Nie obiecujemy
zdalnego usunięcia już wyświetlonych treści ani anulowania wszystkich operacji
rozpoczętych przed cofnięciem sesji. Liczby sesji pokazują stan w chwili odczytu,
a nie liczbę urządzeń. Utrata odpowiedzi może oznaczać, że operacja się wykonała.

## Stan projektu i pozostałe bramki

To nadal lokalna aplikacja demonstracyjna, z symulowanymi płatnościami.
**Natywnego PostgreSQL i Chromium nie zweryfikowano w tym środowisku:**
17 natywnych przypadków PostgreSQL i 2 Chromium mają SKIP. Znane ograniczenia
uruchomienia PostgreSQL przy jedynym UID 0 i przeglądarki opisują poprzednie
raporty; nie uznajemy tych wcześniejszych prób za obecne sukcesy. Nie wykonywano
połączeń z produkcją ani prób obejścia ograniczeń środowiska.

Pozostają m.in. odzyskanie zapomnianego hasła bezpiecznym kanałem, produkcyjne
przekazanie/reemisja PIN-u, bezpieczna weryfikacja sprzedawcy, ustalenie opłat
operatora i dostawcy, rzeczywisty odbiór mobilny oraz niezależna ocena prawna
i bezpieczeństwa przed produkcją. Wersja testowa nie zbiera PESEL, NIP,
daty urodzenia ani rachunku do rzeczywistych wypłat. Adresy dostaw w testowej
bazie nie są szyfrowane jako cała baza; szyfrowanie odpowiedzi checkoutu nie
zastępuje ochrony wszystkich danych. Nie używać prawdziwych danych osobowych.

## Odtwarzalność i przekazanie

Aktualne dowody: `audit_sessions_final_*.json`. Dokumentacja funkcji:
`docs/ZARZADZANIE_SESJAMI.md`. Dodatkowy audyt cofniętych tokenów:
`docs/audits/session_revocation_http.py --report moj_audyt.json`.
Starsze raporty są historią, nie dowodem testów tej wersji.
Przed archiwizacją porównano 413 plików kodu i testów z czystą kopią: identyczne bajty.
ZIP zawiera źródła, testy, dokumentację, lokalny bundle Git, commit źródeł
oraz manifest SHA256. Nie zawiera roboczej bazy, klucza szyfrowania,
plików środowiska ani cache. Lokalny Git można odtworzyć bez GitHub.
