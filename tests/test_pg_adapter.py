from backend.pg_adapter import translate_sql, PgConnection

class Cursor:
    def __init__(self, rows=()): self.rows=list(rows)
    def fetchone(self): return self.rows.pop(0) if self.rows else None
    def __iter__(self): return iter(self.rows)
class Conn:
    def __init__(self): self.calls=[]
    def cursor(self): return Cursor()
    def execute(self, sql, params):
        self.calls.append((sql, params))
        return Cursor([{'id': 42}] if sql.endswith('RETURNING id') else [])

def test_placeholder_translation_preserves_literals():
    assert translate_sql("SELECT '?' AS literal, id FROM users WHERE id=?") == "SELECT '?' AS literal, id FROM users WHERE id=%s"
    assert translate_sql('BEGIN IMMEDIATE') is None

def test_insert_returns_identifier():
    conn=Conn(); result=PgConnection(conn).execute('INSERT INTO users(email,password_hash,role) VALUES(?,?,?)',('a','b','klient'))
    assert result.lastrowid == 42
    assert conn.calls[0][0].endswith('RETURNING id')

def test_non_insert_and_upsert():
    assert translate_sql('UPDATE products SET stock=stock-? WHERE id=?') == 'UPDATE products SET stock=stock-%s WHERE id=%s'
    assert 'RETURNING id' not in translate_sql('INSERT INTO farmer_profiles(user_id) VALUES(?) ON CONFLICT(user_id) DO NOTHING')
