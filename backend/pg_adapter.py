"""PostgreSQL compatibility layer for the existing SQL API.

Opt-in only via DATABASE_URL. Requires psycopg 3; SQLite remains local default.
Do not run schema creation with an application role in production.
"""
import re
from contextlib import contextmanager
from pathlib import Path

try:
    from psycopg.errors import UniqueViolation as PgUniqueViolation
except ImportError:
    class PgUniqueViolation(Exception):
        pass

INSERT_ID = re.compile(r'^\s*INSERT\s+INTO\s+(users|products|orders|pickup_points|payout_plan_batches|payout_reservations|commission_drafts|invoice_drafts|invoice_correction_requests|accounting_audit_events)\s*\(', re.I)


def translate_sql(sql):
    """Translate SQLite positional placeholders without altering SQL literals.

    PostgreSQL dollar-quoted strings, line/block comments and quoted identifiers
    are left intact. This is a compatibility translator, not an SQL validator.
    """
    if sql.strip().upper().rstrip(';').strip() == 'BEGIN IMMEDIATE':
        return None
    out = []
    i = 0
    state = 'normal'
    dollar_tag = None
    block_depth = 0
    while i < len(sql):
        char = sql[i]
        next_char = sql[i + 1] if i + 1 < len(sql) else ''
        if state == 'line_comment':
            out.append(char)
            if char == '\n':
                state = 'normal'
        elif state == 'block_comment':
            if char == '/' and next_char == '*':
                out.extend('/*'); i += 1; block_depth += 1
            elif char == '*' and next_char == '/':
                out.extend('*/'); i += 1; block_depth -= 1
                if block_depth == 0:
                    state = 'normal'
            else:
                out.append(char)
        elif state in ('single', 'double'):
            delim = "'" if state == 'single' else '"'
            out.append(char)
            if char == delim:
                if next_char == delim:
                    out.append(next_char); i += 1
                else:
                    state = 'normal'
        elif state == 'dollar':
            if sql.startswith(dollar_tag, i):
                out.append(dollar_tag)
                i += len(dollar_tag) - 1
                state = 'normal'
            else:
                out.append(char)
        elif char == '-' and next_char == '-':
            out.extend('--'); i += 1; state = 'line_comment'
        elif char == '/' and next_char == '*':
            out.extend('/*'); i += 1; block_depth = 1; state = 'block_comment'
        elif char == "'":
            out.append(char); state = 'single'
        elif char == '"':
            out.append(char); state = 'double'
        elif char == '$':
            match = re.match(r'\$[A-Za-z_][A-Za-z_0-9]*\$|\$\$', sql[i:])
            if match:
                dollar_tag = match.group(0)
                out.append(dollar_tag)
                i += len(dollar_tag) - 1
                state = 'dollar'
            else:
                out.append(char)
        elif char == '?':
            out.append('%s')
        else:
            out.append(char)
        i += 1
    converted = ''.join(out)
    if INSERT_ID.match(converted) and not re.search(r'\bRETURNING\b', converted, re.I):
        stripped = converted.rstrip()
        if stripped.endswith(';'):
            converted = stripped[:-1].rstrip() + ' RETURNING id;'
        else:
            converted = stripped + ' RETURNING id'
    return converted


class PgCursor:
    def __init__(self, cursor, lastrowid=None):
        self.cursor = cursor
        self.lastrowid = lastrowid
        self.rowcount = getattr(cursor, "rowcount", -1)

    def fetchone(self):
        return self.cursor.fetchone()

    def fetchall(self):
        return self.cursor.fetchall()

    def __iter__(self):
        return iter(self.cursor)


class PgConnection:
    def __init__(self, connection):
        self.connection = connection

    def execute(self, sql, params=()):
        # Consume the row only when the compatibility layer added RETURNING id.
        # An explicit RETURNING clause belongs to the caller and must remain
        # available via fetchone()/fetchall(), just like a SELECT result.
        translated = translate_sql(sql)
        if translated is None:
            return PgCursor(self.connection.cursor())
        added_identity = (
            INSERT_ID.match(sql) is not None
            and not re.search(r'\bRETURNING\b', sql, re.I)
            and re.search(r'\bRETURNING\s+id\s*;?\s*$', translated, re.I) is not None
        )
        cursor = self.connection.execute(translated, params)
        identity = cursor.fetchone() if added_identity else None
        lastrowid = identity['id'] if identity is not None else None
        return PgCursor(cursor, lastrowid)


@contextmanager
def postgres_db(url):
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise RuntimeError('PostgreSQL wymaga pakietu psycopg[binary]') from exc
    with psycopg.connect(url, row_factory=dict_row, connect_timeout=5) as connection:
        with connection.transaction():
            yield PgConnection(connection)


def init_postgres(url):
    """Validate schema; apply schema only when WP_AUTO_INIT_POSTGRES=1 (development)."""
    import os
    with postgres_db(url) as con:
        row = con.execute("SELECT to_regclass('public.users') AS table_name").fetchone()
    if row['table_name'] is not None:
        return
    if os.environ.get('WP_AUTO_INIT_POSTGRES') != '1':
        raise RuntimeError('Brak schematu PostgreSQL. Uruchom database/postgres_schema.sql ręcznie.')
    schema = (Path(__file__).resolve().parents[1] / 'database/postgres_schema.sql').read_text()
    import psycopg
    with psycopg.connect(url, connect_timeout=5) as connection:
        connection.execute(schema)

@contextmanager
def postgres_verified_db(url, authorization, *, now=None):
    """Verify a bearer session and run queries with transaction-local actor context.

    This is opt-in groundwork for RLS. Authentication and application queries
    use the SAME connection and transaction. The DB role must still be treated
    as privileged until independently reviewed RLS policies are deployed.
    """
    from .neon_session_bridge import verified_actor

    with postgres_db(url) as connection:
        with verified_actor(connection, authorization, now=now) as actor_id:
            yield connection, actor_id
