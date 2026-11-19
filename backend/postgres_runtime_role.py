"""Reject migration/admin identities at runtime; metadata only, no row contents."""


def assert_runtime_role(connection, *, allow_backup=False):
    row = connection.execute("""SELECT
      EXISTS (SELECT 1 FROM pg_roles r
        WHERE pg_has_role(current_user, r.oid, 'MEMBER')
          AND (r.rolsuper OR r.rolbypassrls OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication
            OR r.rolname IN ('pg_read_all_data','pg_write_all_data','pg_monitor',
              'pg_read_all_settings','pg_read_all_stats','pg_signal_backend',
              'pg_read_server_files','pg_write_server_files','pg_execute_server_program',
              'pg_checkpoint','pg_create_subscription','pg_maintain','pg_use_reserved_connections',
              'wp_rls_guard','wp_rls_executor','wp_migrator','wp_authenticator')
            OR (r.rolname='wp_rls_backup' AND NOT ALLOW_BACKUP))) AS elevated,
      EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname IN ('public','wp_rls','wp_rls_keys','wp_security') AND c.relkind IN ('r','p','v','m','S','f')
          AND pg_has_role(current_user,c.relowner,'MEMBER'))
       OR EXISTS (SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
         WHERE n.nspname IN ('wp_rls','wp_rls_keys','wp_security')
          AND pg_has_role(current_user,p.proowner,'MEMBER')) AS owns_relations,
      has_schema_privilege(current_user,'public','CREATE')
       OR EXISTS (SELECT 1 FROM pg_namespace n WHERE n.nspname IN ('wp_rls','wp_rls_keys','wp_security')
          AND has_schema_privilege(current_user,n.oid,'CREATE')) AS can_create
    """.replace("ALLOW_BACKUP", "true" if allow_backup else "false")).fetchone()
    keys = ('elevated', 'owns_relations', 'can_create')
    values = [row.get(key) for key in keys] if isinstance(row, dict) else list(row or ())
    if len(values) != 3 or any(value is not False for value in values):
        raise RuntimeError('PostgreSQL: wymagane oddzielne, nieuprzywilejowane konto aplikacyjne bez własności tabel i CREATE w public')
