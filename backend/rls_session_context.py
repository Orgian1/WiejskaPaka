"""Candidate RLS context; not enabled in the legacy API until compatibility passes.

Unlike neon_identity.actor_id_sql(), the DB resolves identity from possession of
an active session's *raw* bearer. Changing actor_id/role GUCs has no effect.
Use only inside an explicit transaction; never use connection/session SET.
"""
from contextlib import contextmanager
from .neon_session_bridge import parse_bearer, AuthenticationFailed


@contextmanager
def session_context(connection, authorization):
    token = parse_bearer(authorization)
    connection.execute("SELECT set_config('wiejskapaka.bearer', %s, true)", (token,))
    try:
        row = connection.execute('SELECT wp_security.actor_id() AS actor_id').fetchone()
        actor_id = row['actor_id'] if isinstance(row, dict) else row[0]
        if actor_id is None:
            raise AuthenticationFailed('Sesja nieważna')
        yield actor_id
    finally:
        # On aborted transactions rollback clears LOCAL state. Do not replace
        # the application exception with an InFailedSqlTransaction error.
        import sys
        failing = sys.exc_info()[0] is not None
        try:
            connection.execute("SELECT set_config('wiejskapaka.bearer', '', true)")
        except Exception:
            if not failing:
                raise
