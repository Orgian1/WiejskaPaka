# Pakiety B/61–B/65 — audyt PostgreSQL bez zmian w bazie

- **B/61:** inwentaryzacja roli i tabel w schemacie `public`.
- **B/62:** wykrywanie `SUPERUSER`, `BYPASSRLS`, `CREATEROLE`, `CREATEDB`.
- **B/63:** wykrywanie brakujących tabel, wyłączonego RLS i braku polityk.
- **B/64:** wykrywanie ryzyka obejścia RLS przez właściciela tabeli bez `FORCE ROW LEVEL SECURITY`.
- **B/65:** zapytania wyłącznie `SELECT`, parametryzacja, testy z fałszywym połączeniem.

## Uruchamianie w przyszłości

Wyłącznie po uzyskaniu zgody na połączenie do właściwej bazy i ustawieniu zmiennych środowiskowych prywatnie na serwerze:

```sh
WP_READONLY_PG_PREFLIGHT=YES_I_CONFIRM DATABASE_URL='(ustaw lokalnie, nie wysyłaj w wiadomości)' python scripts/check_postgres_security.py
```

Skrypt **nie został uruchomiony na Neon**. Zwraca kod 2, jeśli znajdzie zagrożenia. Nawet brak wykrytych zagrożeń nie oznacza gotowości do produkcji: wymagane są testy uprawnień na osobnej bazie, polityk RLS i izolacji tenantów. Skrypt nie modyfikuje bazy; używa transakcji tylko do odczytu.
