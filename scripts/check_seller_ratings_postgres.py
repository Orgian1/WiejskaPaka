"""Read-only preflight for seller ratings RLS on a configured PostgreSQL database.

Usage: DATABASE_URL=... python -m scripts.check_seller_ratings_postgres
Never creates tables, grants privileges or modifies production data.
"""
import os
import re
import sys


def check(connection):
    row = connection.execute("""
        SELECT c.relrowsecurity AS enabled, c.relforcerowsecurity AS forced,
               has_table_privilege(current_user, c.oid, 'SELECT') AS can_read,
               has_table_privilege(current_user, c.oid, 'INSERT') AS can_insert,
               has_table_privilege(current_user, c.oid, 'UPDATE') AS can_update,
               has_table_privilege(current_user, c.oid, 'DELETE') AS can_delete
        FROM pg_class c
        WHERE c.oid = to_regclass('public.seller_ratings')
    """).fetchone()
    if row is None:
        raise RuntimeError("Tabela seller_ratings nie istnieje")
    role = connection.execute("""
        SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user
    """).fetchone()
    if role is None or role["rolsuper"] or role["rolbypassrls"]:
        raise RuntimeError("Rola aplikacji omija RLS (SUPERUSER lub BYPASSRLS)")
    policies = connection.execute("""
        SELECT policyname, cmd, qual, with_check, permissive
        FROM pg_policies WHERE schemaname='public' AND tablename='seller_ratings'
    """).fetchall()
    by_name = {p['policyname']: p for p in policies}
    if len(by_name) != len(policies) or set(by_name) != {'seller_ratings_read', 'seller_ratings_buyer_insert'}:
        raise RuntimeError('Nieoczekiwane polityki RLS dla seller_ratings')
    if not row['enabled'] or not row['forced']:
        raise RuntimeError("Brak wymuszonego RLS na seller_ratings")
    if not row['can_read'] or not row['can_insert']:
        raise RuntimeError("Rola aplikacji nie ma SELECT i INSERT do seller_ratings")
    if row['can_update'] or row['can_delete']:
        raise RuntimeError("Rola aplikacji ma niepotrzebne UPDATE lub DELETE")
    if 'seller_ratings_read' not in by_name or by_name['seller_ratings_read']['cmd'] != 'SELECT' or by_name['seller_ratings_read']['permissive'] != 'PERMISSIVE':
        raise RuntimeError("Brak polityki SELECT")
    if (by_name['seller_ratings_read']['qual'] or '').strip().lower() not in ('true', '(true)'):
        raise RuntimeError("Polityka SELECT nie pozwala na publiczne podsumowania ocen")
    insert = by_name.get('seller_ratings_buyer_insert')
    if insert is None or insert['cmd'] != 'INSERT' or insert['permissive'] != 'PERMISSIVE':
        raise RuntimeError("Brak polityki INSERT")
    if insert['qual'] is not None:
        raise RuntimeError("Nieoczekiwany warunek USING w polityce INSERT")
    condition = insert['with_check'] or ''
    # pg_policies returns a deparsed expression; PostgreSQL may strip
    # redundant table qualifiers, so match column identifiers either way.
    for required in ("wiejskapaka.actor_id", "buyer_id", "order_id", "seller_id", "odebrane"):
        if not re.search(r"(?<![a-z_])" + re.escape(required) + r"(?![a-z_])", condition, re.I):
            raise RuntimeError("Polityka INSERT nie sprawdza: " + required)
    # Checking mere identifier presence is insufficient: an unsafe policy
    # could mention all columns without tying them to the order.
    for required in ("EXISTS", "FROM orders", "farmer_id", "o.status"):
        if required.lower() not in condition.lower():
            raise RuntimeError("Polityka INSERT nie weryfikuje zamówienia: " + required)
    print("OK: uprawnienia i polityki ocen RLS sprawdzone dla roli aplikacji (bez zapisu).")


def main():
    url = os.environ.get('DATABASE_URL')
    if not url:
        print("Brak DATABASE_URL: nie wykonano kontroli PostgreSQL.", file=sys.stderr)
        return 2
    try:
        import psycopg
        from psycopg.rows import dict_row
        with psycopg.connect(url, row_factory=dict_row, connect_timeout=5) as con:
            with con.transaction():
                check(con)
        return 0
    except Exception as exc:
        print("Kontrola RLS nie powiodła się: " + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
