# Kwarantanna kolejki po odtworzeniu kopii

Prywatny etap testowy. `backend.reset_mail_queue.quarantine_restored(con)`
jest jawnym krokiem dla operatora odtwarzającego bazę. Nie jest wywoływany
przy zwykłym starcie API ani przy imporcie modułu.

Przed odtworzeniem zatrzymać API i wszystkie procesy wysyłające. Odtwarzać
do odizolowanej bazy, bez uruchamiania pracowników i bez dostępu do dostawcy.
Na tej odtworzonej bazie, wewnątrz `queue.transaction(con)`, wywołać
`queue.quarantine_restored(con)` i zatwierdzić transakcję przed dalszą kontrolą.
Funkcja zwraca liczbę objętych kwarantanną zadań. Nie wymaga kluczy poczty.

Wszystkie zadania `queued` i `leased`, również z rozpoczętą próbą wysyłki,
otrzymują stan `uncertain` i wynik `RESTORE_QUARANTINE`. Szyfrogram, właściciel,
czas dzierżawy i znacznik rozpoczęcia są usuwane. Nie zakładamy, że wiadomość
nie została wysłana po wykonaniu kopii. Historia terminalnych zadań i licznik
prób pozostają zachowane. Ponowne wywołanie nie zmienia już objętych zadań.
Nie wolno ręcznie przywracać tych zadań do `queued`.

Zwykły `recover()` nie zastępuje kwarantanny: może ponownie udostępnić
nierozpoczętą dzierżawę, a zadanie zapisane w kopii jako oczekujące mogło
zostać wysłane później. Operacja wymaga wyłączonych procesów: nie zatrzymuje
transportu, który inny proces wywołał już przed zatwierdzeniem kwarantanny.

To zabezpieczenie zapobiega odtwarzaniu historycznych wysyłek z kolejki.
Nie unieważnia tokenów resetu, sesji ani innych danych przywróconej bazy.
Pełna procedura odtwarzania kont, kopii kluczy, PostgreSQL i odbiór dostawcy
pozostają oddzielnymi zadaniami. Nie jest to polecenie odtwarzania produkcji.

Testy SQLite tworzą rzeczywistą kopię bazy, odtwarzają ją do innego pliku,
zatwierdzają kwarantannę i sprawdzają po ponownym otwarciu, że transport nie
zostaje wywołany także po wygaśnięciu starej dzierżawy. Sprawdzają rollback,
idempotencję, zachowanie historii i brak zmiany oryginału. Osobny scenariusz
natywny PostgreSQL obejmuje transakcję, rollback i odmowę zapisu wyniku przez
starego pracownika. Bramka PostgreSQL wymaga teraz co najmniej 41 zaliczeń.
