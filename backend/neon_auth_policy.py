"""Central rules for bearer sessions and roles; never trust request actor IDs."""
from datetime import datetime, timezone

VALID_ROLES = frozenset({'klient', 'rolnik', 'dostawca', 'admin'})


def normalize_expiry(value):
    """Accept PostgreSQL timestamptz or legacy ISO text, reject naive timestamps."""
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            return None
    if not isinstance(value, datetime) or value.tzinfo is None:
        return None
    try:
        return value.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        return None


def active_session(user_id, expires_at, now):
    if type(user_id) is not int or user_id <= 0:
        return False
    expiry = normalize_expiry(expires_at)
    if expiry is None or not isinstance(now, datetime) or now.tzinfo is None:
        return False
    return expiry > now.astimezone(timezone.utc)


def actor_role(connection, actor_id, allowed):
    """Re-read role on the authenticated transaction; deny missing/unknown roles."""
    from .neon_identity import validate_actor_id
    validate_actor_id(actor_id)
    allowed = frozenset(allowed)
    if not allowed or not allowed <= VALID_ROLES:
        raise ValueError('Nieprawidlowe dozwolone role')
    row = connection.execute('SELECT role FROM users WHERE id=%s', (actor_id,)).fetchone()
    role = row.get('role') if isinstance(row, dict) else (row[0] if row else None)
    return role if role in allowed else None
