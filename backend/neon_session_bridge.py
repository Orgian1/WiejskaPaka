"""PostgreSQL session authentication bridge (not yet wired into FastAPI).

Never accept actor IDs from request bodies. Verify bearer token against the
sessions table using a hashed token before setting a transaction-local identity.
This is not a replacement for row-level security policies.
"""
import hashlib
from datetime import datetime, timezone
from contextlib import contextmanager
from .neon_identity import authenticated_actor
from .neon_auth_policy import active_session


class AuthenticationFailed(PermissionError):
    pass


def parse_bearer(authorization):
    if not isinstance(authorization, str) or not authorization.startswith('Bearer '):
        raise AuthenticationFailed('Brak poprawnego naglowka Bearer')
    token = authorization[7:]
    if not token or len(token) > 4096 or any(c.isspace() for c in token):
        raise AuthenticationFailed('Nieprawidlowy token')
    return token


def authenticate_session(connection, authorization, *, now=None):
    """Return trusted actor id. Caller owns connection and transaction.

    PostgreSQL uses %s parameters. Token is never stored or queried in cleartext.
    """
    token = parse_bearer(authorization)
    digest = hashlib.sha256(token.encode('utf-8')).hexdigest()
    timestamp = now or datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        raise ValueError('Timestamp must include timezone')
    cursor = connection.execute(
        "SELECT s.user_id, s.expires_at FROM sessions s "
        "JOIN users u ON u.id = s.user_id WHERE s.token_hash = %s",
        (digest,),
    )
    row = cursor.fetchone()
    if row is None:
        raise AuthenticationFailed('Sesja nie istnieje')
    if isinstance(row, dict):
        user_id, expires_at = row["user_id"], row["expires_at"]
    else:
        user_id, expires_at = row[0], row[1]
    if not active_session(user_id, expires_at, timestamp):
        raise AuthenticationFailed('Sesja niewazna lub wygasla')
    return user_id


@contextmanager
def verified_actor(connection, authorization, *, now=None):
    """Authenticate and set transaction-local identity on same connection.

    Caller MUST wrap this context in a DB transaction and commit/rollback after.
    """
    actor_id = authenticate_session(connection, authorization, now=now)
    with authenticated_actor(connection, actor_id):
        yield actor_id
