# WiejskaPaka — lokalne testy PostgreSQL

Uruchamiaj wyłącznie w odizolowanym środowisku testowym. Nie korzystaj z Neon,
produkcyjnych danych ani rzeczywistych danych osobowych.

## Docker Compose

Wymagane Docker Engine/Desktop oraz plugin Compose. W katalogu projektu:

```bash
docker compose -f docker-compose.postgres.yml up --abort-on-container-exit --exit-code-from tests
```

Po teście:

```bash
docker compose -f docker-compose.postgres.yml down -v
```

PostgreSQL 16 działa na tymczasowym systemie plików, a port jest udostępniony
wyłącznie na 127.0.0.1:55432. Hasło z Compose jest publicznym hasłem testowym.
Nie wolno używać go w innych środowiskach. Instalowane pakiety są bezpłatne;
nie są uruchamiane GitHub Actions ani usługi płatne.

## Zakres przygotowanej bramy

- starsze testy: połączenie, parametry adaptera, transakcje i rollback;
- `tests/test_postgres_full_api_optin.py`: nowa losowa baza i rola aplikacji,
  komplet migracji, rzeczywisty HTTP do Uvicorn, rejestracja i sesje,
  równoległe ponowienia zakupu z tym samym kluczem, zakup ostatniej sztuki,
  pojedyncza dostawa dla wielu produktów, pełny zwrot i cofnięcie dostępu do adresu,
  pierwotne warunki zakupu, szyfrowany cache oraz odzyskiwanie PIN-u po haśle
  z limitem prób i 100-znakowym kluczem pojedynczego zakupu,
  zmianę hasła oraz wyścig cofnięcia sesji z logowaniem starym hasłem;
- aplikacyjna rola nie ma SUPERUSER, CREATEDB, CREATEROLE ani BYPASSRLS;
  nie ma też uprawnień do tworzenia tabel;
- baza i rola tworzone przez nową bramę mają losowe nazwy i są usuwane po teście;
  istniejące bazy nie są usuwane ani migrowane przez tę bramę.

Można też jawnie ustawić `WP_TEST_POSTGRES_DSN` na lokalny, jednorazowy klaster,
którego konto testowe ma prawo tworzenia baz i ról. Nazwa bazy w DSN musi spełniać
warunek `*_test` albo `wp_test_*`. Nowa brama dopuszcza wyłącznie loopback
lub wewnętrzną nazwę `postgres` z lokalnego Compose. Nie podawaj haseł w czacie.

```bash
python -m pytest -q tests/test_postgres_full_api_optin.py
```

Bez jawnego DSN natywne testy otrzymują **SKIP**, nigdy PASS.

## Rzeczywisty wynik w tej sesji

Sterownik psycopg zainstalowano i pobrano natywne narzędzia PostgreSQL 16.
`initdb` odmówił działania jako root. Środowisko udostępnia wyłącznie mapowanie
UID 0 i nie pozwala przełączyć się na konto nieuprzywilejowane. Docker nie jest
zainstalowany. Dlatego serwer nie wystartował i **integracja PostgreSQL nie jest
zaliczona**. Przygotowany nowy pakiet również pozostaje nieuruchomiony na serwerze.

Ta brama nie zastępuje testów migracji istniejących danych, przeglądu RLS,
audytu prawnego ani weryfikacji operatora płatności.
