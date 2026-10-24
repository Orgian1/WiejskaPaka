import pytest
from database.test_schema_manifest import BASE, UPGRADES, build_manifest, required_startup_tables_covered


def test_manifest_is_unique_and_base_first():
    names = [item['file'] for item in build_manifest()]
    assert names[0] == BASE
    assert len(names) == len(set(names)) == len(UPGRADES) + 1


def test_manifest_hashes_are_deterministic():
    assert build_manifest() == build_manifest()
    assert all(len(item['sha256']) == 64 and item['bytes'] > 0 for item in build_manifest())


def test_missing_migration_fails_closed(tmp_path):
    with pytest.raises(ValueError, match='Missing or empty SQL migration'):
        build_manifest(tmp_path)


def test_all_startup_tables_have_create_statements():
    assert required_startup_tables_covered() == []


def test_manifest_is_read_only_no_connection(monkeypatch):
    import sys
    from types import SimpleNamespace
    monkeypatch.setitem(sys.modules, 'psycopg', SimpleNamespace(connect=lambda *a, **k: pytest.fail('Unexpected DB connection')))
    assert build_manifest()


def test_preview_psql_applies_each_reviewed_migration_once_in_manifest_order():
    import re
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    script=(root/'deploy/preview/new-test-database.psql.example').read_text()
    included=re.findall(r'^\\ir ../../database/(.+)$',script,re.M)
    assert included==[item['file'] for item in build_manifest()]
