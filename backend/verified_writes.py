"""Transaction-bound authorization for PostgreSQL order mutations.

Never derive an actor from request payload. The bearer session is rechecked in
same transaction as writes. SQLite remains a development-only compatibility path.
"""
from contextlib import contextmanager

class WriteAuthorizationError(Exception):
    pass

@contextmanager
def verified_order_write(database_url, authorization, expected_user, allowed_roles):
    from .pg_adapter import postgres_verified_db
    from .neon_auth_policy import actor_role

    with postgres_verified_db(database_url, authorization) as (con, actor_id):
        if actor_id != expected_user['id']:
            raise WriteAuthorizationError('Sesja nie odpowiada użytkownikowi')
        role = actor_role(con, actor_id, tuple(allowed_roles))
        if role is None or role != expected_user['role']:
            raise WriteAuthorizationError('Brak uprawnień do zapisu')
        yield con
