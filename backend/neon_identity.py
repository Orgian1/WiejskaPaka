"""Transaction-scoped identity context for a future PostgreSQL RLS rollout.

Never accept actor_id directly from client input. Authenticate the session in
backend code first, then use this helper inside the SAME DB transaction as
all queries protected by RLS. Not a substitute for deployed RLS policies.
"""
from contextlib import contextmanager
import sys


class IdentityError(ValueError):
    pass


def validate_actor_id(actor_id):
    # bool is a subclass of int and must be rejected.
    if type(actor_id) is not int or actor_id <= 0 or actor_id > 9223372036854775807:
        raise IdentityError('actor_id musi byc dodatnim identyfikatorem BIGINT')
    return actor_id


@contextmanager
def authenticated_actor(connection, actor_id):
    """Set LOCAL context inside a caller-managed transaction.

    Caller must use a fresh transaction or transaction-local context; never
    reuse a prior authenticated identity between requests.
    """
    actor_id = validate_actor_id(actor_id)
    # Parameter binding, never SQL interpolation. `true` => transaction-local.
    connection.execute("SELECT set_config('wiejskapaka.actor_id', %s, true)", (str(actor_id),))
    try:
        yield connection
    finally:
        # A failed PostgreSQL statement may leave the transaction aborted.
        # In that case cleanup SQL itself fails: preserve the original error,
        # and let the outer transaction manager roll back LOCAL settings.
        active_exception = sys.exc_info()[0] is not None
        try:
            connection.execute("SELECT set_config('wiejskapaka.actor_id', '', true)")
        except Exception:
            if not active_exception:
                # Never silently reuse a connection whose identity cannot
                # be cleared. The transaction owner must roll it back.
                raise


def actor_id_sql():
    """SQL expression for future policies; unset/empty identity yields NULL."""
    return "NULLIF(current_setting('wiejskapaka.actor_id', true), '')::bigint"
