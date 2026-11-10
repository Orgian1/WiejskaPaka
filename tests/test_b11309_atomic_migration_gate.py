from pathlib import Path
import pytest
from database.test_schema_safety import check_atomic_test_scripts, _without_comments_and_literals
from database.test_schema_runbook import build_runbook


def test_real_scripts_block_false_atomicity():
    with pytest.raises(ValueError, match='transaction-control'):
        build_runbook()


def test_comments_and_strings_not_interpreted_as_commands():
    assert 'COMMIT' not in _without_comments_and_literals("-- COMMIT\nSELECT 'COMMIT';")


def test_psql_meta_commands_are_blocked(tmp_path, monkeypatch):
    import database.test_schema_safety as safety
    monkeypatch.setattr(safety, 'BASE', 'base.sql')
    monkeypatch.setattr(safety, 'UPGRADES', ())
    (tmp_path / 'base.sql').write_text('SELECT 1;\n\\! echo unsafe\n')
    with pytest.raises(ValueError, match='meta-command'):
        safety.check_atomic_test_scripts(tmp_path)


def test_safe_sample_is_accepted(tmp_path, monkeypatch):
    import database.test_schema_safety as safety
    monkeypatch.setattr(safety, 'BASE', 'base.sql')
    monkeypatch.setattr(safety, 'UPGRADES', ())
    (tmp_path / 'base.sql').write_text('CREATE TABLE example(id integer);')
    assert safety.check_atomic_test_scripts(tmp_path) == 1
