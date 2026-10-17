"""Read-only PostgreSQL preflight for RLS rollout; no policy changes.

RLS must not be enabled until authenticated requests, background jobs and
transaction-scoped identity have integration coverage on real PostgreSQL.
"""

SENSITIVE_TABLES = (
    'users', 'sessions', 'orders', 'order_locations',
    'delivery_assignments', 'seller_compliance',
)


def field(row, key, index):
    return row[key] if isinstance(row, dict) else row[index]


def inspect_rls(connection):
    """Return a conservative, read-only report for sensitive tables."""
    rows = connection.execute(
        "SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity, "
        "COALESCE((SELECT COUNT(*) FROM pg_policy p WHERE p.polrelid = c.oid), 0) AS policy_count "
        "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = %s AND c.relkind IN ('r','p') "
        "AND c.relname = ANY(%s)",
        ('public', list(SENSITIVE_TABLES)),
    ).fetchall()
    by_name = {field(r, 'relname', 0): {'enabled': bool(field(r, 'relrowsecurity', 1)),
                'forced': bool(field(r, 'relforcerowsecurity', 2)),
                'policy_count': int(field(r, 'policy_count', 3))} for r in rows}
    report = {}
    for name in SENSITIVE_TABLES:
        entry = by_name.get(name)
        if entry is None:
            report[name] = {'status': 'missing'}
        elif not entry['enabled']:
            report[name] = {'status': 'rls_disabled', **entry}
        elif not entry['policy_count']:
            report[name] = {'status': 'rls_without_policies', **entry}
        else:
            report[name] = {'status': 'manual_review_required', **entry}
    return {'ready_for_public_launch': False, 'tables': report,
            'warning': 'RLS flags alone do not prove authorization. Verify API and database roles.'}
