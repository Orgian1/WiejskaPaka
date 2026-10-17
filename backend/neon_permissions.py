"""Read-only review of database role privileges. Never exports user data or secrets."""
import json
import os

SENSITIVE_TABLES = ('users', 'sessions', 'order_locations', 'orders', 'delivery_assignments', 'seller_compliance')


def audit_permissions(connection, role='wiejskapaka_app'):
    """Report structural exposure; not a substitute for application authorization or RLS."""
    with connection.cursor() as cur:
        cur.execute('SELECT rolcanlogin, rolsuper, rolcreatedb, rolcreaterole, rolbypassrls FROM pg_roles WHERE rolname=%s', (role,))
        flags = cur.fetchone()
        if flags is None:
            return {'role_exists': False, 'safe_admin_flags': False, 'tables': {}, 'production_ready': False}
        cur.execute('SELECT has_schema_privilege(%s, %s, %s)', (role, 'public', 'CREATE'))
        can_create = bool(cur.fetchone()[0])
        cur.execute('SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname=%s AND tablename=ANY(%s)', ('public', list(SENSITIVE_TABLES)))
        rls = dict(cur.fetchall())
        privileges = {}
        for table in SENSITIVE_TABLES:
            cur.execute('SELECT has_table_privilege(%s, %s, %s)', (role, 'public.' + table, 'SELECT'))
            privileges[table] = {'select': bool(cur.fetchone()[0]), 'rls': bool(rls.get(table, False))}
    safe_flags = bool(flags[0] and not any(flags[1:]) and not can_create)
    exposed = sorted(t for t, p in privileges.items() if p['select'] and not p['rls'])
    return {'role_exists': True, 'safe_admin_flags': safe_flags, 'tables': privileges,
            'tables_without_rls_with_select': exposed, 'production_ready': False}


def main():
    url = os.environ.get('DATABASE_URL')
    if not url:
        raise SystemExit('Brak DATABASE_URL. Ustaw go prywatnie na serwerze; nie wysyłaj do czatu.')
    import psycopg
    with psycopg.connect(url, connect_timeout=5) as connection:
        report = audit_permissions(connection)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report['tables_without_rls_with_select'] or not report['safe_admin_flags']:
        raise SystemExit('UWAGA: Dostęp do danych wymaga dodatkowych zabezpieczeń. Nie uruchamiaj publicznie.')


if __name__ == '__main__':
    main()
