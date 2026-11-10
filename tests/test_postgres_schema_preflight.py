from backend.postgres_schema_preflight import CORE_TABLES, check_core_schema

class FakeConnection:
    def __init__(self, names, mapping=False):
        self.names = names
        self.mapping = mapping
        self.calls = []
    def execute(self, sql, params):
        self.calls.append((sql, params))
        class Cursor:
            def __init__(self, rows): self.rows = rows
            def fetchall(self): return self.rows
        rows = [{'table_name': n} if self.mapping else (n,) for n in self.names]
        return Cursor(rows)

def test_all_core_tables_present():
    con = FakeConnection(CORE_TABLES)
    result = check_core_schema(con)
    assert result['core_schema_complete']
    assert result['missing'] == []
    assert result['ready_for_public_launch'] is False
    assert con.calls[0][1][0:2] == ('public', 'BASE TABLE')

def test_missing_table_blocks_core_readiness():
    con = FakeConnection(['users', 'orders'], mapping=True)
    result = check_core_schema(con)
    assert not result['core_schema_complete']
    assert 'sessions' in result['missing']
    assert 'order_locations' in result['missing']

def test_empty_schema_is_not_ready():
    result = check_core_schema(FakeConnection([]))
    assert result['found'] == 0
    assert len(result['missing']) == len(CORE_TABLES)
