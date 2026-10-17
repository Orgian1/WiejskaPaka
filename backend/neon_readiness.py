"""Read-only PostgreSQL readiness checks for the test backend.

Requires DATABASE_URL from the server environment; never prints connection secrets.
This is a structural check, NOT a security audit or production approval.
"""
import os

REQUIRED_TABLES = (
    'users', 'sessions', 'login_attempts', 'products', 'farmer_profiles',
    'pickup_points', 'orders', 'order_locations', 'delivery_assignments',
    'order_events', 'notifications', 'payment_simulations',
    'payment_simulation_events', 'seller_compliance', 'schema_migrations',
)
REQUIRED_COLUMNS = {
    'users': ('id', 'email', 'password_hash', 'role'),
    'orders': ('id', 'buyer_id', 'farmer_id', 'product_id', 'pin_hash', 'pin_attempts', 'pin_used'),
    'order_locations': ('order_id', 'delivery_city', 'delivery_street', 'delivery_postal_code'),
    'payment_simulations': ('order_id', 'total_grosze', 'products_grosze', 'delivery_grosze', 'commission_grosze', 'seller_grosze'),
}


def check_schema(connection):
    """Use read-only catalog queries; returns diagnostics, not any user data."""
    with connection.cursor() as cur:
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'")
        tables = {row[0] for row in cur.fetchall()}
        cur.execute("SELECT table_name, column_name FROM information_schema.columns WHERE table_schema='public'")
        columns = {}
        for table, column in cur.fetchall():
            columns.setdefault(table, set()).add(column)
        cur.execute("SELECT rolcanlogin, rolbypassrls, rolsuper, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname=current_user")
        role = cur.fetchone()
        cur.execute("SELECT has_schema_privilege(current_user,'public','CREATE')")
        can_create = bool(cur.fetchone()[0])
        cur.execute("SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname='public' AND tablename IN ('users','orders','order_locations','delivery_assignments','seller_compliance')")
        rls = {name: enabled for name, enabled in cur.fetchall()}
    missing_tables = sorted(set(REQUIRED_TABLES) - tables)
    missing_columns = {name: sorted(set(expected) - columns.get(name, set())) for name, expected in REQUIRED_COLUMNS.items() if set(expected) - columns.get(name, set())}
    role_safe = bool(role and role[0] and not any(role[1:]) and not can_create)
    return {
        'table_count': len(tables),
        'missing_tables': missing_tables,
        'missing_columns': missing_columns,
        'limited_app_role': role_safe,
        'rls_enabled': rls,
        'schema_compatible': not missing_tables and not missing_columns,
        'production_ready': False,
    }


def main():
    url = os.environ.get('DATABASE_URL', '').strip()
    if not url:
        raise SystemExit('Brak DATABASE_URL w zmiennych środowiskowych backendu (nie wklejaj go do czatu).')
    import psycopg
    with psycopg.connect(url, connect_timeout=5) as connection:
        result = check_schema(connection)
    import json
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result['schema_compatible'] or not result['limited_app_role']:
        raise SystemExit('Kontrola wykazała braki; nie uruchamiaj aplikacji publicznie.')
    print('Struktura zgodna z kontrolowanym zakresem. RLS i testy integracyjne nadal wymagane.')


if __name__ == '__main__':
    main()
