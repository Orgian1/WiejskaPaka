"""PostgreSQL views must never be locked or treated as destination tables."""
from pathlib import Path


def test_preflight_excludes_views():
    sql = Path('database/postgres_preflight.py').read_text()
    assert "t.table_type = 'BASE TABLE'" in sql
    assert 'JOIN information_schema.tables t' in sql


def test_migrator_excludes_views():
    sql = Path('database/migrate_all_tables.py').read_text()
    assert "t.table_type = 'BASE TABLE'" in sql
    assert 'JOIN information_schema.tables t' in sql
