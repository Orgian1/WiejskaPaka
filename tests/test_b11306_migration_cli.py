from pathlib import Path
from database.verify_test_migrations import main, verify
from database.test_schema_manifest import BASE, UPGRADES


def test_project_sql_files_all_accounted_for():
    result = verify()
    assert result['ok']
    assert len(result['files']) == len(UPGRADES) + 1
    assert result['execution_performed'] is False


def test_untracked_sql_fails_closed(tmp_path):
    source = Path(__file__).resolve().parents[1] / 'database'
    for name in (BASE, *UPGRADES):
        (tmp_path / name).write_bytes((source / name).read_bytes())
    (tmp_path / 'unexpected.sql').write_text('DROP TABLE users;')
    result = verify(tmp_path)
    assert not result['ok']
    assert result['untracked_sql'] == ['unexpected.sql']


def test_missing_file_returns_error_without_executing(tmp_path, capsys):
    assert main(['--directory', str(tmp_path)]) == 1
    assert 'execution_performed' in capsys.readouterr().out


def test_cli_success(capsys):
    assert main([]) == 0
    assert '"ok": true' in capsys.readouterr().out
