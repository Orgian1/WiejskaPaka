from pathlib import Path
import subprocess
import shutil
import pytest

from database.generate_test_migration_plan import generate
from database.test_schema_manifest import UPGRADES


def test_plan_is_anchored_and_fails_before_migration_if_no_psql():
    plan = generate()
    assert plan.startswith('#!/bin/sh\n')
    assert 'set -eu' in plan
    assert 'cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)"' in plan
    assert plan.index('cd "$(CDPATH=') < plan.index('python -m database.verify_test_migrations')
    assert plan.index('command -v psql') < plan.index('python -m database.validate_migration_target')
    assert plan.count('psql -X') == len(UPGRADES) + 1


@pytest.mark.skipif(shutil.which('sh') is None, reason='POSIX shell is not installed; generated plan is a shell artifact')
def test_generated_shell_syntax(tmp_path):
    output = tmp_path / 'plan.sh'
    output.write_text(generate())
    result = subprocess.run(['sh', '-n', str(output)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_generator_still_rejects_wrong_structure(monkeypatch):
    import pytest
    import database.generate_test_migration_plan as mod
    monkeypatch.setattr(mod, 'build_sequential_plan', lambda *args: {'script': 'set -e\n'})
    with pytest.raises(ValueError, match='Unexpected'):
        mod.generate()
