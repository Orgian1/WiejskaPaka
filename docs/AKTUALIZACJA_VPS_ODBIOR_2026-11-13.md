# WiejskaPaka — procedura aktualizacji i wycofania do odbioru

**Procedura dla operatora, niewykonana. Nie jest poleceniem zmiany VPS.**
Nie odczytywano w tej sesji bieżącego stanu VPS. Nazwy usług, ścieżki, baza,
reverse proxy i porty muszą być ustalone z rzeczywistej konfiguracji. Zachować
obecny podgląd, jego adres, bazę i procesy; nowe wydanie najpierw obok niego.

## 1. Inwentaryzacja bez zmian

Zapisać prywatnie pełny SHA starego wydania, gałąź, lokalne zmiany (także pliki
nieśledzone/ignorowane), wersję Pythona i PostgreSQL, konfigurację usług i workerów,
porty, domeny, magazyn zdjęć oraz aktywne flagi. Sprawdzić health i działające
logowanie. Nie drukować plików środowiska ani poświadczeń do publicznego raportu.
Nie używać `git reset --hard`, `git clean` ani `pull` w działającym katalogu.

Wydanie docelowe pochodzi wyłącznie z `codex/demo-finalization-fixes-20261112`
repozytorium `Orgian1/WiejskaPaka`. Przypiąć pełny SHA z końcowego raportu i
potwierdzić zgodność z origin. Nie przełączać `main`. Stare wydanie i venv
zachować w całości, również gdy mają niezacommitowane pliki.

## 2. Kopia i rzeczywista próba odtworzenia

Przed migracją trwałej bazy operator ustala okno techniczne i wstrzymuje jej
zapisy, workery, cykliczne zadania i przyjmowanie webhooków. Zapisać ich stan,
aby odtworzyć dokładnie poprzednią konfigurację. Zachować razem:

- spójną kopię bazy (dla SQLite także poprawne uwzględnienie WAL),
- komplet obecnych kluczy sejfu zakupów, kolejek, rotacji i kopii zapasowych,
- pliki zdjęć/zewnętrznych zasobów, konfigurację i uprawnienia,
- stare wydanie, zależności i definicje usług/reverse proxy.

Kopie są prywatne, szyfrowane i poza repozytorium, z kontrolą sum i uprawnień.
Klucz deszyfrujący przechowywać oddzielnie. Nie generować nowych kluczy do starej
bazy. Nie kopiować samego aktywnego pliku SQLite przez `cp`.

Dla PostgreSQL operator używa zgodnego `pg_dump` (co najmniej wersji serwera)
i formatu custom, np. po przygotowaniu prywatnych wpisów `pg_service.conf` oraz
`.pgpass`, bez haseł w wierszu poleceń. Poniższy **szablon** wymaga prawdziwych,
zweryfikowanych przez operatora nazw usług i klucza odbiorcy:

```bash
set -o pipefail
umask 077
pg_dump --dbname='service=WP_SOURCE_REVIEWED' --format=custom --no-owner \
  | gpg --encrypt --recipient OPERATOR_BACKUP_KEY --output /private/backup/pre-update.dump.gpg
```

Sprawdzić kod zakończenia całego potoku; nie nadpisywać poprzedniej kopii.
Odtworzyć kopię w **nowej, izolowanej** bazie bez dostępu poczty/płatności,
np. strumieniem `gpg --decrypt` do zgodnego `pg_restore --exit-on-error
--no-owner --no-privileges --dbname='service=WP_RESTORE_REVIEWED'`. Docelowy serwis
musi wskazywać pustą bazę próbnego odtworzenia, nigdy oryginał. Uprawnienia
odtworzyć według spisanej konfiguracji, nie przez nadanie aplikacji superusera.
Potwierdzić liczby rekordów, relacje, salda, rezerwacje i odszyfrowanie zakupów
w izolacji, z sesjami i kolejkami poddanymi kwarantannie. Samo `pg_restore --list`
nie jest próbą przywrócenia. Dla SQLite użyć mechanizmu backup API/snapshot
zgodnego z [procedurą odtwarzania](ODZYSKIWANIE_OPERACJI_PORTFELA_2026-11-10.md).
Narzędzia projektu ograniczone do jednorazowych baz testowych nie służą do
kopiowania produkcji — nie omijać ich zabezpieczeń.

## 3. Migracje najpierw na kopii

Nowy katalog wydania i osobny venv; instalacja z `requirements-lock.txt`.
`python -m database.verify_test_migrations` kontroluje manifest i sumy **44 plików**,
ale nie wykonuje SQL i nie dowodzi zgodności istniejącej bazy.

Manifest `database/test_schema_manifest.py` i
`deploy/preview/new-test-database.psql.example` tworzą **nową pustą bazę testową**.
Nie uruchamiać całego łańcucha ani podstawowego `postgres_schema.sql` na istniejącej
bazie: nie wszystkie skrypty są wielokrotnego użytku. Operator porównuje rzeczywisty
schemat i historię zastosowanych migracji, przygotowuje plan samych brakujących
zmian i wykonuje go najpierw na odtworzonej kopii z `ON_ERROR_STOP=1`.
Skrypty zawierają własne transakcje — nie zakładać, że zewnętrzne `-1` utworzy
jedną transakcję całego łańcucha.

Sprawdzić szczególnie:

| Funkcja | Migracja / tabele do potwierdzenia |
| --- | --- |
| Ulubione i lokalizacja | `optional_account_favorites.sql` |
| Kody na trzy punkty | `optional_pickup_promotions.sql` |
| Propozycje terminów | `optional_delivery_schedule_proposals.sql` |
| Kolejność punktów na koncie | **nowa** `optional_seller_navigation.sql`: `seller_navigation(user_id, revision, point_ids)` |
| Portfel | `wallet_preview_terms`, `wallet_preview_resolutions`, `wallet_preview_operation_fences` i pozostałe tabele wymagane przez aktywne flagi |

Nowa tabela nawigacji nie zmienia zamówień ani współrzędnych. Punkty bez zapisanej
kolejności pojawiają się według ID; kolejne punkty są dopisywane do końca.
Dotychczasowy zapis kolejności z localStorage nie jest automatycznie importowany:
po aktualizacji sprzedawca ustawia ją raz i zapis staje się wspólny dla urządzeń.

Nadać roli aplikacji tylko wymagane uprawnienia do nowych tabel; użytkownik
aplikacji nie wykonuje DDL. Potwierdzić startup, pełne działanie aktywnych flag,
transakcje, FK i brak powtórnego księgowania płatności w próbnym wydaniu.
Sprawdzić również kopiowanie nowej tabeli w używanej przez operatora procedurze
backupu/migracji danych. Nie migrować SQLite do PostgreSQL jako ukrytej części
aktualizacji kodu; to osobna operacja z własną próbą odtworzenia.

## 4. Kandydat obok obecnego podglądu

Nowa usługa, nowy katalog, nowy prywatny port i oddzielna baza odbiorowa. Nie
przepinać istniejącego podglądu ani jego domeny. Nie łączyć starego i nowego kodu
z tą samą bazą podczas prób. Odtworzona baza wymaga izolacji danych i sekretów;
najprostszy odbiór właściciela wykorzystuje fikcyjne dane demo.

Nie kopiować konfiguracji prawdziwego PayU ani uruchamiać workerów wysyłających
historyczną pocztę. Symulowane płatności wyłącznie w odizolowanym, zabezpieczonym
demo. Launcher `run_phone_demo.py` tworzy jednorazową lokalną SQLite i nie służy
do uruchomienia trwałej bazy VPS. Nowy opcjonalny tryb `--host` z certyfikatem
HTTPS służy do odbioru w prywatnej sieci Wi-Fi; nie jest wdrożeniem VPS. Konfigurację trwałego preview oprzeć o istniejące
`deploy/preview/preview.env.example`, guardy i `backend.test_server_launcher`;
przetestować całą konfigurację i nie ustawiać trybu produkcyjnego w celu obejścia
guardów. Nowe demo nie może mieć dostępu do produkcyjnych webhooków.

Photon w demo wymaga jawnego `WP_ENABLE_ADDRESS_SEARCH=1`,
`WP_ADDRESS_SEARCH_PROVIDER=photon`,
`WP_ADDRESS_SEARCH_URL=https://photon.komoot.io/api/` oraz ruchu HTTPS do tego
hosta. Publiczny profil tylko jeden worker i małe użycie; przy większym użyciu
własny Photon. Osobno opcjonalne kafelki `tile.openstreetmap.org`.
Brak Photon nie może blokować mapy/GPS. GPS na telefonie wymaga HTTPS i zgody.

Odbiór: [lista właściciela](ODBIOR_WLASCICIELA_2026-11-13.md), health, cztery role,
telefon/desktop, ulubione, kolejność z dwóch urządzeń, rezerwacje, propozycje dat,
jedna opłata dostawy, jednorazowy PIN, zwroty, portfel 5%/0%, raport i prywatność.
Przed ewentualnym przełączeniem operator zapisuje wyniki i zgodę właściciela na
konkretny SHA, zakres oraz okno. Ta instrukcja nie upoważnia do wdrożenia.

## 5. Przełączenie i rollback

Po osobnej decyzji operator przełącza wyłącznie uzgodniony wskaźnik wydania/usługę;
poprzedni podgląd zachowuje jako niezależny punkt powrotu. Zaraz sprawdzić health,
logowanie i scenariusze krytyczne. 500, błąd schematu, utrata danych, błędne saldo,
ponowne użycie PIN-u lub ujawnienie danych wstrzymują odbiór.

Rollback kodu: wstrzymać nowe zapisy i workery, zachować prywatną kopię stanu po
awarii, przywrócić poprzedni kod/venv/konfigurację i sprawdzić zgodność z aktualnym
schematem. Dodatkową tabelę nawigacji zwykle pozostawia się w bazie — nie usuwać
jej i nie próbować automatycznie odwracać wszystkich migracji. Zgodność starego
kodu z pozostałymi zmianami wymaga próby przed przełączeniem.

Nie przywracać starej bazy automatycznie po przyjęciu nowych zamówień: utraciłoby
to ich zapis. Jeśli zgodność uniemożliwia rollback kodu, operator uzgadnia
odtworzenie i rozliczenie operacji z okresu zmiany; zachowuje oba stany i wszystkie
klucze. Nie usuwać blokad idempotencji, warunków wypłat ani decyzji portfela.
Stary kod bez ich obsługi wymaga wyłączenia zapisów portfela. Kolejki i sesje
odtworzone z kopii pozostają w kwarantannie do kontroli, aby nie powtórzyć wysyłek
i operacji. Po powrocie sprawdzić PIN-y, rezerwacje, salda i dostęp do zakupów.
