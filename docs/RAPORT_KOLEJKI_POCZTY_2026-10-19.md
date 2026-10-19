# Kolejka resetu — 19.10.2026

Kod: 47bbfe3c98b2f5bb191b1f91cb44910d7688b46b.
CI: https://github.com/Orgian1/WiejskaPaka/actions/runs/39212529571
PR: https://github.com/Orgian1/WiejskaPaka/pull/7

## Wynik funkcjonalny

Dodano osobny moduł reset_mail_queue dla syntetycznej SQLite. Wydanie tokenu,
limit i zadanie mogą zostać zatwierdzone wspólnie. Adres oraz oryginalny token
są szyfrowane AES-256-GCM z uwierzytelnieniem metadanych. Nieznany adres nie
otrzymuje zadania; adres do wysyłki pochodzi z zapisanego konta.

Zadania są przejmowane dzierżawą. dispatch_once zatwierdza znacznik rozpoczęcia
przed wywołaniem jawnie dostarczonego transportu i nie utrzymuje wtedy blokady
SQLite. Stary właściciel nie może nadpisać wyniku. Awaria po rozpoczęciu próby
prowadzi do uncertain bez automatycznego ponowienia. Jawne odmowy przejściowe
mogą zostać ponowione maksymalnie do trzech prób, przed wygaśnięciem linku.
W stanach terminalnych usuwany jest szyfrowany ładunek.

Szczegóły i wymagania wywołującego: KOLEJKA_RESETU_SQLITE.md.

Migracja upgrade_z_reset_mail_queue.sql deklaruje odpowiednik tabeli PostgreSQL.
Jest dołączona do manifestu 26 plików, zamka sum kontrolnych i szablonu
przygotowania nowej testowej bazy. W szablonie usunięto zdublowany wpis
nowej migracji sprzed schematu bazowego; sprawdzono dokładną kolejność
26 wpisów i wszystkie sumy. Szablon nie był wykonywany na serwerze.
Migracja nie włącza wykonywania zadań na PostgreSQL.

## Kontrola i dowody

Pierwszy pakiet kontrolny: 98 zaliczonych testów, w tym 50 nowych przypadków kolejki.
Pełny Linux tego etapu ujawnił brak tabeli w odpowiedniku schematu PostgreSQL:
3945 zaliczonych, 1 błąd, 49 pominiętych. Kontrola raportu wydania pozostała
niezmieniona. Dodano migrację i natywny test ograniczeń zamiast pomijać tabelę
w audycie. Po tej poprawce pakiet obejmujący raport, runner, zamek schematu
i kolejkę zaliczył 90 testów. Poprzedni wynik zachowano oddzielnie w
katalogu mail_queue_417ace5_2026-10-19 jako etap zastąpiony.
Pozostałe dotyczą resetu, adaptera SMTP i polityki kanałów. Wyników tych nie
sumować z pełną regresją, która obejmuje te same przypadki.

Dwa osobne procesy Linux zostały celowo przerwane przez os._exit(73).
W pierwszym przypadku niezapisany znacznik rozpoczęcia został wycofany,
a zadanie wznowiono. W drugim przerwanie po wywołaniu transportu pozostawiło
trwały znacznik: po restarcie zadanie stało się uncertain. W obu scenariuszach
transport w pamięci został wywołany łącznie jeden raz. To kontrola restartu
procesu i transakcji, nie utraty zasilania lub działania rzeczywistego SMTP.

Odrębna próba ośmiu pracowników na 48 zadaniach zakończyła się 48 przyjęciami,
bez duplikatów i bez pozostawionych szyfrowanych ładunków. To lokalna kontrola
konkurencji, a nie pomiar wydajności VPS lub dowód obsługi ruchu produkcyjnego.

Skrócone dowody znajdują się w audits/mail_queue_47bbfe3_2026-10-19/.
Pobierane artefakty CI są sprawdzane przez sumę SHA-256 archiwum, odciski
źródeł oraz znaczniki success, complete i sources_unchanged.

| Bramka | Zaliczone | Błędy | Pominięte | Stan |
| --- | ---: | ---: | ---: | --- |
| Pełny Linux, 319/319 modułów | 3946 | 0 | 50 | sukces |
| Pełny Windows, 319/319 modułów | 3920 | 0 | 76 | sukces |
| PostgreSQL 16, aplikacja i ograniczenia tabeli | 28 | 0 | 0 | sukces |
| Chromium i realny HTTP | 36 | 0 | 0 | sukces; HTTP w pięciu rozmiarach |
| Szybki Windows | 80 | 0 | 0 | sukces |

Wszystkie bramki zakończyły się sukcesem. Pełne przebiegi zachowały
niezmienione źródła. Liczby zaliczeń i pominięć są rozdzielone; natywne
bramki nie są doliczane do sum regresji.

## Granice

Nie dodano migracji do startu aplikacji, trasy HTTP, procesu w tle ani
włączenia SMTP. Moduł wymaga jawnie dostarczonych połączenia, kluczy,
zegara i transportu. Produkcyjne zarządzanie kluczami i retencja metadanych
nie są zaimplementowane. Nie potwierdzono własności skrzynek użytkowników.

PostgreSQL wymaga osobnej implementacji wykonywania zadań i odbioru
uprawnień pracownika; nowa migracja dotyczy przechowywania. Natywna bramka
sprawdza dotychczasowy zakres aplikacji oraz ograniczenia nowej tabeli.
Nie przedstawiać jej jako testu wykonującej wysyłki kolejki PostgreSQL.

Nie wykonano rzeczywistej wysyłki, konfiguracji dostawcy, DNS, hostingu ani
płatności. Nie zmieniono prowizji, podziału zwrotów, PIN-ów lub opłat dostawy.
Rolnik i sprzedawca pozostają tą samą rolą. To kolejny zakończony zakres
techniczny po odbiorze bramek, nie dopuszczenie aplikacji do produkcyjnej sprzedaży.
