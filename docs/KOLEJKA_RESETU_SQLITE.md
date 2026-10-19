# Odłączona kolejka resetu SQLite

Stan: 19.10.2026. Implementacja backend/reset_mail_queue.py stanowi osobny
moduł testowany na syntetycznej bazie SQLite. Nie jest wywoływana przez
backend/app.py, nie tworzy tabel przy starcie aplikacji i nie ma domyślnego
transportu, konfiguracji środowiskowej, harmonogramu ani procesu w tle.
Nie podłączono SMTP, PostgreSQL, hostingu ani płatności w ramach tego etapu.

## Co działa w module

- Wydanie linku, zapis jego hasha, limity i utworzenie zadania mogą być
  zatwierdzone w jednej transakcji. Wyjątek cofa całość przez transaction().
- Nieznany adres nadal zużywa limit resetu, ale nie tworzy zadania. Odbiorca
  jest pobierany z konta, nie przekazywany bezpośrednio z żądania do transportu.
- Adres i oryginalny token są szyfrowane AES-256-GCM z losowym nonce.
  Uwierzytelnione metadane wiążą ładunek z zadaniem, kontem, zdarzeniem,
  hashem tokenu, wersją klucza oraz czasem utworzenia i wygaśnięcia.
- Osobny KeyRing jest przekazywany jawnie przez wywołującego. Dopuszcza
  zachowanie starszych wersji przy rotacji; nie tworzy klucza po restarcie.
  Nie korzysta z klucza sejfu zamówień lub hasła SMTP. Kod nie ma jeszcze
  produkcyjnego ładowania i zarządzania kluczami; nie wprowadzać ich do repo.
- BEGIN IMMEDIATE serializuje piszących pracowników. Zadanie ma losowego
  właściciela dzierżawy. Spóźniony właściciel nie może zatwierdzić wyniku.
- Tuż przed próbą sprawdzane są ważność linku, wersja hasła i zgodność konta
  oraz adresu odbiorcy. Uszkodzony ładunek lub brak klucza kończy zadanie
  bez transportu. Taki wynik wymaga nowego żądania resetu, nie ślepego retry.
- Przed wywołaniem transportu dispatch_once zatwierdza trwały znacznik próby.
  Wysyłka nie utrzymuje blokady zapisu SQLite. Błąd tego commit blokuje wysyłkę.
- Utracona dzierżawa sprzed rozpoczęcia próby może wrócić do kolejki.
  Utracona dzierżawa po rozpoczęciu jest niepewna i nie jest ponawiana.
- Jawna odmowa przejściowa ma ograniczone ponowienia: maksymalnie trzy
  próby, odstępy 30 i 60 sekund, wyłącznie przed wygaśnięciem linku.
- ACCEPTED oznacza przyjęcie przez SMTP, nie dostarczenie do skrzynki.
  Niepewny wynik DATA, nieobsłużony wyjątek transportu i nieprawidłowy wynik
  transportu trafiają do uncertain bez automatycznego ponowienia.
- Stany terminalne usuwają szyfrowany ładunek. Zapisywane są tylko ustalone
  kody wyniku, a nie odpowiedzi dostawcy, tokeny lub treść wiadomości.

## Użycie wyłącznie jawne

Wywołujący przygotowuje osobną bazę z tabelami resetu i SCHEMA kolejki;
żadne nowe DDL nie zostało dodane do startu aplikacji. Połączenie wymaga
sqlite3.Row. Mutacje muszą być objęte transaction(con). Nie łapać wyjątku
wydania zadania wewnątrz transakcji i nie zatwierdzać częściowego wyniku.

Do wykonania jednej próby służy dispatch_once(connect, keys, transport,
clock=...). Każda zależność jest obowiązkowa. connect tworzy osobne
połączenie; funkcja je zamyka. clock zwraca sekundy UTC jako liczbę całkowitą.
Transport jest jawnie dostarczoną funkcją i powinien mieć ograniczony czas
wykonania krótszy od dzierżawy. Domyślna dzierżawa to 120 sekund, dozwolone
30–300. Przeterminowany wynik nie nadpisuje stanu: późniejsze recover()
klasyfikuje rozpoczętą próbę jako uncertain.

Niskopoziomowe claim/start/finish służą również testom awarii. Oryginalny
token zwrócony przez start wolno przekazać do transportu dopiero PO
pomyślnym commit. dispatch_once zapewnia tę kolejność. Nie ma gwarancji
dokładnie jednokrotnego dostarczenia przez SMTP; wybrano ochronę przed
ponownym wysłaniem po niepewnej próbie kosztem możliwego braku wiadomości.

## Granice odbioru i dalsze prace

Testy używają prawdziwych transakcji SQLite, ponownie otwieranych połączeń,
dwóch pracowników oraz podstawionego transportu SMTP w pamięci. Sprawdzają
też awarie commit przed wysyłką i po potwierdzonym przyjęciu, integralność
szyfrowania, rotację kluczy, limity oraz unieważnienie przez reset hasła.
Nie odbierają dostarczenia, DNS, certyfikatu dostawcy ani obciążenia produkcji.

Przed użyciem aplikacyjnym potrzebne są implementacja i odbiór PostgreSQL,
wersjonowane migracje i uprawnienia, prywatne ładowanie kluczy, retencja
metadanych/audytu, zasady odtwarzania kopii bez ponownego wysłania starych
zadań, ograniczona pętla pracownika i bezpieczne ogólne odpowiedzi HTTP.
Sam moduł nie implementuje potwierdzania własności adresu e-mail ani
powiadomień o zamówieniach. Rolnik i sprzedawca pozostają tą samą rolą.

Kontrakt docelowy: KONTRAKT_KOLEJKI_POCZTY.md. Ten etap realizuje jego
część SQLite; pozostałe wymagania nie są uznane za wykonane.
