"""Read-only PostgreSQL readiness inspection; never changes database state.

This is diagnostic evidence, NOT certification of RLS or production safety.
"""

SENSITIVE_TABLES = ('users', 'sessions', 'orders', 'delivery_addresses', 'courier_assignments', 'farmer_profiles')


def inspect_postgres(connection):
    """Inspect table existence, RLS flags and the current role's privileges.

    The supplied connection must be authenticated by the caller. All queries
    are static and read-only; no actor context or database mutation is made.
    """
    results = []
    for table in SENSITIVE_TABLES:
        row = connection.execute(
            """SELECT c.relrowsecurity AS rls_enabled,
                      c.relforcerowsecurity AS rls_forced,
                      (SELECT count(*) FROM pg_catalog.pg_policies p
                       WHERE p.schemaname = 'public' AND p.tablename = ?) AS policy_count,
                      has_table_privilege(current_user, c.oid, 'SELECT') AS can_select
               FROM pg_catalog.pg_class c
               JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
               WHERE n.nspname = 'public' AND c.relname = ? AND c.relkind IN ('r', 'p')""",
            (table, table),
        ).fetchone()
        results.append({
            'table': table,
            'exists': row is not None,
            'rls_enabled': bool(row['rls_enabled']) if row else False,
            'rls_forced': bool(row['rls_forced']) if row else False,
            'policy_count': int(row['policy_count']) if row else 0,
            'can_select': bool(row['can_select']) if row else False,
        })
    return {
        'tables': results,
        'requires_review': True,
        'rls_is_not_verified': True,
        'missing_tables': [r['table'] for r in results if not r['exists']],
        'rls_disabled': [r['table'] for r in results if r['exists'] and not r['rls_enabled']],
    }
