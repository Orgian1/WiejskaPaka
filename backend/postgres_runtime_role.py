"""Reject migration/admin identities at runtime; metadata only, no row contents."""


def assert_runtime_role(connection):
    row = connection.execute("""SELECT
      EXISTS (SELECT 1 FROM pg_roles r
        WHERE pg_has_role(current_user, r.oid, 'MEMBER')
          AND (r.rolsuper OR r.rolbypassrls OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication
            OR r.rolname IN ('pg_read_all_data','pg_write_all_data','pg_monitor',
              'pg_read_all_settings','pg_read_all_stats','pg_signal_backend',
              'pg_read_server_files','pg_write_server_files','pg_execute_server_program',
              'pg_checkpoint','pg_create_subscription','pg_maintain','pg_use_reserved_connections'))) AS elevated,
      EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='public' AND c.relkind IN ('r','p','v','m','S','f')
          AND pg_has_role(current_user,c.relowner,'MEMBER')) AS owns_relations,
      has_schema_privilege(current_user,'public','CREATE') AS can_create
    """).fetchone()
    keys = ('elevated', 'owns_relations', 'can_create')
    values = [row[key] for key in keys] if isinstance(row, dict) else list(row or ())
    if len(values) != 3 or any(value is not False for value in values):
        raise RuntimeError('PostgreSQL: wymagane oddzielne, nieuprzywilejowane konto aplikacyjne bez własności tabel i CREATE w public')
