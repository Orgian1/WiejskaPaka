"""Read-only Neon security readiness audit. No schema changes or secrets."""

SENSITIVE_TABLES = ('users', 'orders', 'order_locations', 'delivery_assignments', 'seller_compliance')


def field(row, key, index):
    return row[key] if isinstance(row, dict) else row[index]


def audit_security(connection):
    """Return actionable findings; safe to run as an owner in SQL Editor.

    This is a configuration audit, not proof of end-to-end authorization.
    """
    rows = connection.execute(
        "SELECT tablename, rowsecurity FROM pg_catalog.pg_tables "
        "WHERE schemaname = %s AND tablename = ANY(%s)",
        ('public', list(SENSITIVE_TABLES)),
    ).fetchall()
    flags = {field(row, 'tablename', 0): bool(field(row, 'rowsecurity', 1)) for row in rows}
    findings = []
    for table in SENSITIVE_TABLES:
        if table not in flags:
            findings.append({'table': table, 'severity': 'error', 'issue': 'missing_table'})
        elif not flags[table]:
            findings.append({'table': table, 'severity': 'warning', 'issue': 'rls_disabled'})
    return {'checked': len(flags), 'rls_enabled': sum(flags.values()),
            'ready_for_public_launch': False, 'findings': findings}
