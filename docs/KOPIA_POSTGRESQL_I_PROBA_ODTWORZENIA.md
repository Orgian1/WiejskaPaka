# Szyfrowana kopia PostgreSQL i próba odtworzenia

Narzędzie `scripts/postgres_test_backup.py` obsługuje lokalną bazę testową
PostgreSQL 16 i narzędzia pg_dump/pg_restore 16 na POSIX. Nie obsługuje Neon,
serwerów zdalnych, bazy produkcyjnej ani odtworzenia do wskazanej istniejącej
bazy. Rozmiar dumpu ograniczono do 64 MiB, pojedynczy proces do 120 sekund.
To rozwiązanie do podglądu/testów, nie system kopii dla docelowej skali.

## Klucze i pliki

Kopia zawiera dump w formacie custom oraz odpowiadający mu klucz sejfu
odpowiedzi zakupu. Całość chroni AES-256-GCM z losowym nonce, niezależnym
kluczem kopii i uwierzytelnionym nagłówkiem. Klucza kopii nie wolno trzymać
w katalogu archiwów ani używać jako klucza sejfu. Klucze pozostają poza
repozytorium; operator musi przechować bezpieczną kopię klucza szyfrującego
oddzielnie od archiwów. Utrata klucza uniemożliwi odtworzenie.

Nowe archiwum publikowane jest atomowo, z prawami 0600, bez nadpisywania
istniejącego pliku. Dump nie jest zapisywany jako jawny plik na dysku;
klucz wewnętrzny podczas sprawdzania trafia do prywatnego pliku tymczasowego.
Plaintext istnieje w pamięci procesów; narzędzie nie chroni przed
administratorem systemu, pamięcią wymiany ani złośliwym oprogramowaniem.
Wstrzymać rotację klucza sejfu na czas wykonywania kopii.

## Przygotowanie

Przykładowe prywatne lokalizacje: `/srv/wp-backups` dla archiwów,
`/srv/wp-backup-keys` dla klucza; oba katalogi 0700 i dostępne tylko operatorowi.
Utworzenie tych katalogów i uprawnień należy do administratora. Klucz sejfu
zachowuje istniejącego właściciela — nie zmieniać praw na publiczne, aby
umożliwić backup. Operację przeprowadzać jako jego uprawniony właściciel.

```bash
python -m scripts.postgres_test_backup init-key \
  --backup-key /srv/wp-backup-keys/preview.backup-key
```

Polecenie tworzy nowy klucz i odmawia zastąpienia istniejącego.
URL bazy przekazać jako WP_TEST_DATABASE_URL prywatnie, bez zapisu w historii,
np. `read -r -s WP_TEST_DATABASE_URL` i `export WP_TEST_DATABASE_URL`.
Nazwa musi mieć postać `wp_test_*` lub `*_test`, host loopback/localhost.
Kopia korzysta z ograniczonej roli aplikacji; sprawdza jej uprawnienia
administracyjne, tożsamość bazy i rdzeń schematu. Wymusza odczyt bez zapisu.

```bash
python -m scripts.postgres_test_backup backup \
  --checkout-key /var/lib/wiejskapaka/checkout-key.json \
  --backup-key /srv/wp-backup-keys/preview.backup-key \
  --destination /srv/wp-backups/preview-2026-10-19.wpbackup
unset WP_TEST_DATABASE_URL
```

Sukces kopii daje `restore_verified=false`: samo zapisanie pliku nie
potwierdza odzyskiwalności danych. Nie wysyła się haseł w argumentach
pg_dump/pg_restore ani w wyniku JSON; nie dziedziczy się ustawień PGSERVICE,
PGHOSTADDR ani PGOPTIONS. Uprawnienia administratora systemu nadal umożliwiają
wgląd do pamięci i środowiska procesu.

## Próba odtworzenia

Uruchamiać wyłącznie własne, zaufane kopie. Dump PostgreSQL może zawierać
wykonywalne SQL; poprawne szyfrowanie nie czyni cudzego dumpu bezpiecznym.
Próbę najlepiej wykonywać na odizolowanym lokalnym klastrze testowym.
WP_TEST_POSTGRES_DSN wskazuje jego bazę startową o nazwie testowej i konto
administrujące z prawem tworzenia/usuwania baz. Nie umieszczać tego konta
w konfiguracji aplikacji ani nie przekazywać hasła w czacie.

```bash
python -m scripts.postgres_test_backup rehearse \
  --archive /srv/wp-backups/preview-2026-10-19.wpbackup \
  --backup-key /srv/wp-backup-keys/preview.backup-key
unset WP_TEST_POSTGRES_DSN
```

Najpierw sprawdzane są uwierzytelnienie archiwum, rozmiary i klucz sejfu.
Dopiero potem tworzona jest losowa baza `wp_test_restore_*`. pg_restore
wykonuje odtworzenie w jednej transakcji, zatrzymując się na błędzie.
Sprawdzenie obejmuje odszyfrowanie zapisanych odpowiedzi zakupu i audyt
spójności symulacji płatności. Odtworzone sesje i tokeny resetu hasła
są usuwane, aby nie przenieść dawnych uprawnień do odzyskanego środowiska.

Po próbie baza jest usuwana, także po błędzie odtworzenia/walidacji.
`rehearsal_database_removed=true` pojawia się dopiero po udanym usunięciu.
Jeśli proces zostanie zabity lub klaster straci łączność, administrator
sprawdza pozostawione bazy testowe; narzędzie nie usuwa ich zbiorczo.
Źródłowa baza, sesje i działająca aplikacja pozostają nietknięte.

## Granice wyniku

Próba nie uruchamia odtworzonego API i nie promuje kopii do użycia.
Odtworzenie produkcyjne wymaga osobnego procesu nadawania ról i uprawnień,
odtworzenia klucza w docelowej lokalizacji, konfiguracji usługi i odbioru HTTP.
Kopia jednej bazy nie obejmuje kont systemowych, konfiguracji VPS, DNS,
poczty, ról globalnych PostgreSQL, zewnętrznych plików ani odtwarzania PITR.
Kopiowanie poza serwer i harmonogram nie zostały włączone automatycznie.
