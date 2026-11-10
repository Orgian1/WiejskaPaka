"""Regression: preflight must cover all tables queried by FastAPI lifespan."""
import ast
from pathlib import Path

import pytest

from backend.postgres_schema_preflight import CORE_TABLES
from backend.test_server_launcher import verify_test_database_connection

REQUIRED = ('inventory_reservations', 'order_purchase_records', 'pickup_point_coordinates')


def test_all_lifespan_tables_covered():
    source = (Path(__file__).resolve().parents[1] / 'backend' / 'app.py').read_text()
    tree = ast.parse(source)
    lifespan = next(node for node in tree.body if isinstance(node, ast.AsyncFunctionDef)
                    and node.name == 'application_lifespan')
    literals = [node.value for node in ast.walk(lifespan)
                if isinstance(node, ast.Constant) and isinstance(node.value, str)]
    for table in REQUIRED:
        assert any(f'FROM {table} ' in value for value in literals)
        assert table in CORE_TABLES
    assert len(CORE_TABLES) == len(set(CORE_TABLES))


class Cursor:
    def __init__(self, tables): self.tables = tables; self.query = ''
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def execute(self, query, params=None):
        self.query = query
        if 'information_schema.tables' in query:
            assert params == ('public', 'BASE TABLE', list(CORE_TABLES))
    def fetchone(self):
        return (False, False, False, False) if 'pg_roles' in self.query else ('wp_test',)
    def fetchall(self): return [(table,) for table in self.tables]


class Connection:
    def __init__(self, tables): self.tables = tables; self.closed = False
    def cursor(self): return Cursor(self.tables)
    def close(self): self.closed = True


@pytest.mark.parametrize('missing', REQUIRED)
def test_missing_lifespan_table_blocks_listener(missing):
    con = Connection([table for table in CORE_TABLES if table != missing])
    with pytest.raises(RuntimeError, match=missing):
        verify_test_database_connection('postgresql://unused/wp_test', 'wp_test',
                                        connect=lambda *args, **kwargs: con, require_schema=True)
    assert con.closed


def test_all_required_tables_pass():
    con = Connection(CORE_TABLES)
    verify_test_database_connection('postgresql://unused/wp_test', 'wp_test',
                                    connect=lambda *args, **kwargs: con, require_schema=True)
    assert con.closed
