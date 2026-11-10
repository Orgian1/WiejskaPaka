"""Read-only PostgreSQL security inventory; never changes permissions or RLS.

The output is intentionally conservative: metadata cannot prove isolation.
"""

from .neon_rls_preflight import SENSITIVE_TABLES


def _value(row, key, index):
    return row[key] if isinstance(row, dict) else row[index]


def inspect_security(connection):
    """Inspect current database role and RLS of sensitive public tables.

    All SQL is SELECT only; no credentials or row contents are returned.
    """
    role = connection.execute(
        "SELECT current_user, current_database(), "
        "r.rolsuper, r.rolbypassrls, r.rolcreaterole, r.rolcreatedb "
        "FROM pg_roles r WHERE r.rolname = current_user"
    ).fetchone()
    if role is None:
        raise RuntimeError('Nie można odczytać uprawnień roli PostgreSQL')
    flags = {
        'superuser': bool(_value(role, 'rolsuper', 2)),
        'bypass_rls': bool(_value(role, 'rolbypassrls', 3)),
        'create_role': bool(_value(role, 'rolcreaterole', 4)),
        'create_database': bool(_value(role, 'rolcreatedb', 5)),
    }
    rows = connection.execute(
        "SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity, "
        "pg_get_userbyid(c.relowner) = current_user AS is_owner, "
        "has_table_privilege(current_user, c.oid, 'SELECT') AS can_select, "
        "has_table_privilege(current_user, c.oid, 'INSERT') AS can_insert, "
        "has_table_privilege(current_user, c.oid, 'UPDATE') AS can_update, "
        "has_table_privilege(current_user, c.oid, 'DELETE') AS can_delete, "
        "(SELECT COUNT(*) FROM pg_policy p WHERE p.polrelid = c.oid) AS policies "
        "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = %s AND c.relkind IN ('r','p') "
        "AND c.relname = ANY(%s)",
        ('public', list(SENSITIVE_TABLES)),
    ).fetchall()
    found = {}
    for row in rows:
        name = _value(row, 'relname', 0)
        found[name] = {
            'rls_enabled': bool(_value(row, 'relrowsecurity', 1)),
            'rls_forced': bool(_value(row, 'relforcerowsecurity', 2)),
            'role_owns_table': bool(_value(row, 'is_owner', 3)),
            'select': bool(_value(row, 'can_select', 4)),
            'insert': bool(_value(row, 'can_insert', 5)),
            'update': bool(_value(row, 'can_update', 6)),
            'delete': bool(_value(row, 'can_delete', 7)),
            'policy_count': int(_value(row, 'policies', 8)),
        }
    findings = []
    if flags['superuser'] or flags['bypass_rls']:
        findings.append('Rola aplikacji może ominąć RLS')
    if flags['create_role'] or flags['create_database']:
        findings.append('Rola aplikacji ma podwyższone uprawnienia administracyjne')
    tables = {}
    for name in SENSITIVE_TABLES:
        info = found.get(name)
        if info is None:
            findings.append(f'Brak tabeli: {name}')
            tables[name] = {'status': 'missing'}
            continue
        tables[name] = info
        if not info['rls_enabled']:
            findings.append(f'RLS wyłączone: {name}')
        if info['rls_enabled'] and info['policy_count'] == 0:
            findings.append(f'RLS bez polityk: {name}')
        if info['role_owns_table'] and not info['rls_forced']:
            findings.append(f'Właściciel tabeli może ominąć RLS: {name}')
    return {
        'role': str(_value(role, 'current_user', 0)),
        'database': str(_value(role, 'current_database', 1)),
        'role_flags': flags,
        'tables': tables,
        'findings': findings,
        'ready_for_production': False,
        'note': 'Metadane nie potwierdzają izolacji danych. Wymagane testy polityk i API na osobnej bazie.',
    }
