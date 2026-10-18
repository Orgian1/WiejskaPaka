# Wznowienie z rozmowy „Wynik testów WiejskaPaka” — 18.10.2026

Gałąź robocza: `wiejskapaka-import`. `main` pozostaje bez zmian.
Kod bieżącego pakietu: `4f629cc2a9f09ea158547c3c5ebc964f9dd7089d`.
CI: https://github.com/Orgian1/WiejskaPaka/actions/runs/39117437209

## Zachowany i połączony zakres

Pobrano zmiany do commitu `f4cf5fab709cd8bff04eac7dabe9201127eb525d`
z drugiego czatu: politykę komunikacji e-mail/panel bez SMS, powiązanie
resetu hasła z tą polityką, plan skali polskiego pilotażu i pierwszego celu,
narzędzia szacowania ruchu oraz roboczy regulamin i rejestr zagadnień prawnych.
Zachowano je przy dodaniu czytelnego panelu finansowego administratora i CSV.
Nie uruchomiono rzeczywistej wysyłki poczty ani integracji produkcyjnych.

## Naprawione raportowanie Windows

Przebieg `39111056052` dla `f4cf5fa` zaliczył PostgreSQL, Chromium i szybki
Windows, lecz pełny Windows przerwał zapis raportu: `checked_counts(None)`
powodował nieobsłużony TypeError. Nie ma podstaw do przypisania mu liczby
zaliczonych testów ani statusu PASS.

Runner odrzuca teraz brakujące lub nieprawidłowe liczniki kontrolowanym
błędem `INVALID_TEST_RESULT`. Zachowuje wyłącznie dozwolone nazwy modułów
niezaliczonych, niekompletnych i tych z przekroczonym czasem. Zapisuje
oczyszczony raport, bez prywatnych logów i bez zastępowania brakujących
liczników zerami. Nowe cztery przypadki regresji odtwarzają ten problem.
Nie ustalono retrospektywnie, który moduł nie dostarczył liczników w tamtym
przebiegu; nowa diagnostyka ma zachować tę informację przy powtórzeniu.

## Start rzeczywistego HTTP w testach

Pierwsza pełna regresja po wznowieniu zakończyła się trzema błędami gotowości
serwera: dwa przypadki w `test_pin_recovery_http.py` i jeden w
`test_sqlite_recovery_rehearsal.py`. Podczas pracy równoległej wraz z testem obciążenia
serwery pozostawały uruchomione, ale nie zgłaszały gotowości w pięciosekundowym
budżecie wspólnego helpera.

Helper czeka teraz do 20 sekund czasu monotonicznego, z limitem 0,5 sekundy
na pojedynczą kontrolę zdrowia. Natychmiast odrzuca zakończony proces.
Po błędzie lub zakończeniu scenariusza nadal kończy i oczekuje na proces.
Test kontrolowanego zegara potwierdza start po ponad pięciu sekundach,
twarde zakończenie oczekiwania, odrzucenie martwego serwera i sprzątanie
po błędzie klienta testowego. Nie zmieniono backendu ani kryterium zdrowia.

## Potwierdzone kontrole

| Zakres | Wynik |
| --- | --- |
| Reporter CI, helper HTTP, panel finansowy, polityka powiadomień i planowanie skali | 72 zaliczone, bez błędów i pominięć |
| Rzeczywiste HTTP: PIN, odtworzenie kopii, restart i sejf zakupów | 24 zaliczone, bez błędów i pominięć |
| Lokalna akceptacja zakupów, dostaw, zwrotów i prywatności | Cztery zadania PASS |
| Minutowy test współbieżnego HTTP/SQLite | PASS: 106 rund, 995 żądań, 2483 sprawdzenia niezmienników |
| Pełna regresja Linux po poprawce helpera | 308/308 modułów; 3771 zaliczonych, 0 błędów, 35 pominiętych; razem 3806 przypadków |
| Natywny PostgreSQL | 17/17, bez błędów i pominięć |
| Natywne Chromium | 23/23, bez błędów i pominięć; ponadto rzeczywiste HTTP przy pięciu szerokościach |
| Natywny szybki Windows | 80/80, bez błędów i pominięć |
| Pełny Windows | Trwa; brak jeszcze końcowego wyniku |

Artefakty dla bieżącego kodu: `audits/restored_ci_4f629cc2_2026-10-18`.
Archiwa pobrano z Actions, sprawdzono ich SHA-256 oraz zgodność wszystkich
odcisków kodu, testów, helperów, zależności i workflow z lokalnym projektem.

Zestawy celowane częściowo się pokrywają i należą również do pełnej regresji.
Liczników obciążenia nie należy dodawać do liczby odrębnych przypadków testów.
HTTP i test obciążenia wykonano na tym samym kodzie aplikacji przed zmianą
wyłącznie helpera testowego. Nie są pomiarem produkcyjnego PostgreSQL ani
potwierdzeniem zdolności obsługi 5000 kupujących dziennie.

Natywne PostgreSQL 17/17, Chromium 23/23 z pięcioma szerokościami HTTP i szybki
Windows 80/80 zaliczyły też wcześniejszy kod `af832502`; oczyszczone artefakty
mają osobny katalog `audits/restored_ci_af832502_2026-10-18` i plik pochodzenia.
Nie zastępują testów nowego zestawu źródeł i helperów.

Historyczny pełny Windows dla `da3ca749` został pobrany i zweryfikowany:
3722 zaliczone, 0 błędów, 40 pominiętych. Jego odciski są zgodne z zapisanym
szybkim raportem tego samego starego kodu. Nie jest wynikiem obecnego pakietu.

## Dalszy odbiór

Końcowy pełny raport Linux: `audits/restored_linux_2026-10-18.json`.

Sprawdzić pełny Windows dla bieżącego commitu. Jeśli wynik jest niekompletny,
rozwiązać moduły wskazane w nowej oczyszczonej diagnostyce i ponowić kontrolę.
Rozbieżności roboczego regulaminu z funkcjami zapisano w
`MAPA_REGULAMINU_I_FUNKCJI_PL.md`: w szczególności panel reklamacji, częściowa
odmowa odbioru i rzeczywiste e-maile wymagają implementacji oraz osobnego
odbioru. Roboczy dokument nie został opublikowany w interfejsie.
