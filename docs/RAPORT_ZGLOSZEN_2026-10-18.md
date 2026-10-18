# Prywatny panel zgłoszeń problemów — 18.10.2026

Kod: `aa0f7f6573ce3c418b5cf113975a7ecc1d846acd` na `wiejskapaka-import`.
CI: https://github.com/Orgian1/WiejskaPaka/actions/runs/39119179853
Instrukcja odbioru i kontrakt API: `ZGLOSZENIA_PROBLEMOW_TESTOWE.md`.

## Zachowanie

Kupujący otwiera testową sprawę przy zamówieniu lub przesyłce. Dla pozycji
należącej do przesyłki zapis jest powiązany z całą przesyłką. Opis i historię
widzą wyłącznie kupujący, właściwy sprzedawca i administrator. Dostawca nie
ma dostępu. Lista nie zawiera swobodnej treści ani danych kontaktowych kont.

Uczestnicy mogą odpowiadać. Administrator nadaje stan obsługi lub zamyka
sprawę testowo; do ponownego otwarcia również potrzebny jest administrator.
Każdy wpis zwiększa całkowitą wersję. Stary widok nie nadpisuje nowszej
odpowiedzi. Identyfikator ponowienia chroni przed drugim zapisem tej samej
operacji; po utracie odpowiedzi interfejs zachowuje go dla niezmienionej
wysyłanej treści w tym widoku. Po odświeżeniu lub wylogowaniu szkic znika.

Nie dodano automatycznych decyzji, terminów, poczty, anulowania, zwrotów,
częściowego odbioru ani zmian rozliczenia. Potwierdza to test porównujący
zamówienia, stany produktów i wszystkie powiązane symulacje płatności
przed i po obsłudze sprawy. To przepływ testowy, a nie kompletna procedura
produkcyjnych reklamacji.

## Dostęp i spójność

| Operacja | Uprawnienia i warunek |
| --- | --- |
| Utworzenie | Tylko kupujący istniejącego zakupu; serwer wyznacza sprzedawcę i powiązanie z przesyłką |
| Lista i szczegóły | Własne sprawy klienta, sprawy zakupów danego rolnika, cała kolejka administratora |
| Odpowiedź | Uczestnik sprawy lub administrator, zgodna bieżąca wersja |
| Zamknięcie / ponowne otwarcie | Administrator i wpis z uzasadnieniem; bez skutku finansowego |
| Powtórzenie żądania | Ten sam autor, klucz, treść i żądany stan; zmiana treści z tym samym kluczem daje 409 |
| Wylogowanie / zmiana konta | Usunięcie prywatnego widoku i szkiców, odrzucenie opóźnionych odpowiedzi w UI |

Zapis korzysta z istniejącej ponownej autoryzacji sesji w transakcji.
SQLite używa BEGIN IMMEDIATE, PostgreSQL blokuje sprawę do odpowiedzi,
a utworzenia z tym samym kluczem serializuje na kupującym. Dwie różne
odpowiedzi z tej samej wersji nie zostają obie zapisane. Zegar nie jest
identyfikatorem wersji. Tabele testowego modułu dodano do przeglądanego
schematu i blokady sum kontrolnych dla nowej izolowanej bazy PostgreSQL.

Wszystkie opisy są wstawiane do DOM jako tekst. Kontrolowany przykład
HTML pozostaje tekstem; kod nie używa innerHTML dla treści sprawy.
Swobodnej treści nie anonimizujemy automatycznie, dlatego formularze
wymagają używania fikcyjnych danych i ostrzegają przed podawaniem haseł,
PIN-ów, telefonów i danych dokumentów. Nie przekazano rzeczywistych danych
ani nie podłączono zewnętrznej bazy.

## Sprawdzenie

| Kontrola | Wynik |
| --- | --- |
| Pełna regresja Linux | 311/311 modułów; 3784 zaliczone, 0 błędów, 38 pominiętych; razem 3822 przypadki |
| Końcowe kontrole HTTP, UI i kolejności skryptów | 27/27, bez pominięć |
| Natywny PostgreSQL | 18/18, bez błędów i pominięć, w tym pełny przepływ zgłoszeń |
| Natywne Chromium | 25/25, bez błędów i pominięć, w tym zgłoszenia przy 320/1280 px; ponadto pięć szerokości rzeczywistego HTTP |
| Szybki Windows | 80/80, bez błędów i pominięć |
| Pełny Windows | Brak jeszcze wyniku dla tego pakietu |

Dowody lokalne: `audits/support_linux_2026-10-18.json` oraz
`audits/support_targeted_2026-10-18.json`. Pominięcia obejmują bramki
wymagające natywnych środowisk; nie stanowią ich zaliczenia. Powtórzone
zestawy celowane są podzbiorem pełnej regresji, a nie dodatkowymi przypadkami.

Testy rzeczywistego HTTP sprawdzają role i obce konta, ponowienia utworzenia
oraz odpowiedzi, zmienioną treść z tym samym kluczem, dwie decyzje równoległe,
zamknięcie i ponowne otwarcie, wcześniejsze strony historii, brak skutku
finansowego, restart procesu i wyłączony tryb testowy. Kontrole JavaScript
obejmują czyszczenie szkiców, zmianę konta i spóźnione odpowiedzi, najnowszą
listę oraz podwójne kliknięcie i ponowienie po utracie odpowiedzi.

Poprzedni pełny Windows dla `4f629cc2` zakończył się sukcesem: 3766 zaliczonych,
0 błędów, 40 pominiętych. Artefakt i zgodność jego odcisków z pozostałymi
bramkami tego samego kodu są zapisane w `audits/restored_ci_4f629cc2_2026-10-18`.
Nie jest to wynik nowego modułu zgłoszeń.

## Dodatkowy odbiór kopii i dokumentacja

Wykonano osobną próbę akceptacyjną rzeczywistego HTTP z szyfrowaną kopią
nowych danych. Odtworzono sprawę w wersji 2 wraz z dwoma wpisami; wpis
zapisany po kopii pozostał wyłącznie w źródle. Stara sesja dała 401, świeże
logowanie klienta i rolnika zachowało właściwy dostęp, a dostawca dostał 403.
Sprawdzono cztery zakupy, cztery symulacje płatności, integralność SQLite
i klucze obce. To dodatkowy scenariusz akceptacyjny, nie nowa liczba przypadków
pytest. Oczyszczony wynik: `audits/support_restore_acceptance_2026-10-18.json`.

`PRYWATNOSC_INWENTARYZACJA_I_PROJEKT_PL.md` opisuje stan faktyczny danych,
pamięć przeglądarki, skrzynkę resetu i brak ustalonej ogólnej retencji.
Roboczą część informacyjną odniesiono do oficjalnego tekstu RODO w EUR-Lex.
Nie jest to gotowa polityka do publikacji ani ocena całego modelu prawnego.
`WZNOWIENIE_PO_WYLACZENIU_WINDOWS.md` podaje bezpieczny scenariusz nowej
kopii kodu, startu demo i odróżnienia jednorazowych danych od zapisów GitHuba.
