# Odtwarzanie bazy i kluczy z kwarantanną kolejki

Próba odzyskiwania używa istniejącej zaszyfrowanej kopii bazy z kluczem sejfu
zamówień oraz osobnego archiwum wersjonowanych kluczy poczty. Archiwa mają
niezależne klucze szyfrujące. Ich przygotowanie wymaga zatrzymania rotacji
i utrzymania zgodności wersji po stronie operatora; nie jest to jeden atomowy
pakiet bazy i wszystkich kluczy.

## Blokada historycznych zadań

SQLite `snapshot(..., restore=True)` w nowym katalogu oraz natywna próba
PostgreSQL w nowej jednorazowej bazie unieważniają sesje i linki resetu,
a następnie poddają aktywną kolejkę kwarantannie w tej samej transakcji:

| Stan w kopii | Stan po odtworzeniu |
| --- | --- |
| queued | expired |
| leased bez started_at | expired |
| leased z started_at | uncertain |
| accepted / uncertain / failed / expired | Bez zmiany historii |

Zmienione wpisy otrzymują RESTORE_QUARANTINED. Ich ładunek, właściciel,
dzierżawa i znacznik rozpoczęcia są usuwane; liczba prób pozostaje zachowana.
Nie odtwarza się dostarczenia z samego braku wyniku. Ponowna kwarantanna
nie zmienia już zakończonych wpisów. Bezpośrednia funkcja
`reset_mail_queue.quarantine_restored` wymaga transakcji i jest przeznaczona
wyłącznie do odtwarzanej, odłączonej kopii — nie należy wywoływać jej na
działającej bazie źródłowej.

Zwykłe wykonanie backupu nie modyfikuje kolejki ani bazy źródłowej.
SQLite obsługuje też wcześniejsze kopie bez tabeli reset_mail_queue.
Jeżeli usunięcie sesji/tokenów lub kwarantanna nie powiedzie się, transakcja
jest wycofywana, niepełny katalog odtworzenia SQLite usuwany, a jednorazowa
baza próby PostgreSQL usuwana przez blok finally. Istniejące cele nie są
nadpisywane. Publiczne pola dotychczasowego raportu odzyskiwania zachowano.

## Kontrole próbne

Lokalny scenariusz tworzy rzeczywiste testowe zakupy, tokeny i trzy zadania:
oczekujące, przejęte bez rozpoczęcia oraz przejęte z trwałym znacznikiem
rozpoczęcia. Wykonuje zaszyfrowaną kopię bazy i osobną kopię kluczy poczty,
odtwarza je w nowych lokalizacjach i sprawdza:

- brak odtworzonych sesji i tokenów resetu;
- expired/expired/uncertain, brak ładunków i brak zadań dla transportu;
- prawidłowe odzyskanie klucza do oryginalnego sztucznego ładunku;
- niezmienione zamówienia i integralność bazy;
- niezmieniony skrót pliku źródłowego i jego aktywna kolejka;
- usunięcie niepełnego celu po wymuszonej awarii kwarantanny.

Natywny scenariusz PostgreSQL przygotowuje obie kopie, odtwarza klucze,
wykonuje pg_restore do nowej losowej bazy, sprawdza brak zadań do przejęcia
w odtworzonej kopii oraz usuwa ją po próbie. Baza źródłowa pozostaje bez zmian.
Ten scenariusz wymaga wykonanego odbioru CI; sama definicja nie jest wynikiem.

Nie uruchamia się automatycznie API, pracownika ani SMTP. Przywrócone klucze
nie podmieniają aktywnego pliku. Ponowne dopuszczenie ruchu, nadzorca usługi,
kontrola uprawnień, procedura operatora i odbiór dostawcy są osobnymi krokami.
