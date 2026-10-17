from pathlib import Path
import pytest
from database.generate_test_migration_plan import generate, main
from database.test_schema_manifest import UPGRADES


def test_plan_checks_hashes_before_target_and_migration():
    plan = generate()
    assert plan.index('python -m database.verify_test_migrations') < plan.index('python -m database.validate_migration_target')
    assert plan.index('python -m database.validate_migration_target') < plan.index('psql -X')
    assert plan.count('psql -X') == len(UPGRADES) + 1
    assert 'set -eu' in plan


def test_generator_refuses_overwrite(tmp_path, monkeypatch):
    import database.generate_test_migration_plan as module
    monkeypatch.setattr(module, 'generate', lambda: 'safe\n')
    root = Path(module.__file__).resolve().parents[1]
    output = root / '.b11315_test_plan.sh'
    try:
        output.write_text('existing')
        with pytest.raises(SystemExit):
            main(['--output', str(output)])
        assert output.read_text() == 'existing'
    finally:
        output.unlink(missing_ok=True)


def test_generator_writes_private_file(monkeypatch):
    import database.generate_test_migration_plan as module
    monkeypatch.setattr(module, 'generate', lambda: 'safe\n')
    root = Path(module.__file__).resolve().parents[1]
    output = root / '.b11315_test_plan.sh'
    try:
        assert main(['--output', str(output)]) == 0
        assert output.read_text() == 'safe\n'
        assert output.stat().st_mode & 0o777 == 0o600
    finally:
        output.unlink(missing_ok=True)
