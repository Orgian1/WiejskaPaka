"""Exercise the batch launcher with Windows CMD."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import venv

import pytest

LAUNCHER = Path(__file__).resolve().parents[1] / 'START_DEMO_WINDOWS.cmd'
pytestmark = pytest.mark.skipif(sys.platform != 'win32', reason='requires Windows CMD')


def launch(folder):
    return subprocess.run(
        ['cmd.exe', '/d', '/c', LAUNCHER.name],
        cwd=folder,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        errors='replace',
        env={**os.environ, 'PIP_DISABLE_PIP_VERSION_CHECK': '1', 'PIP_NO_INDEX': '1'},
        timeout=120,
    )


def test_launcher_requires_full_extraction(tmp_path):
    shutil.copyfile(LAUNCHER, tmp_path / LAUNCHER.name)

    result = launch(tmp_path)

    assert result.returncode == 1
    assert 'Wyodrebnij wszystkie' in result.stdout
    assert not (tmp_path / '.venv-demo').exists()


def test_launcher_recovers_environment_with_missing_pip(tmp_path):
    project = tmp_path / 'Wiejska Paka demo'
    (project / 'scripts').mkdir(parents=True)
    (project / 'backend').mkdir()
    shutil.copyfile(LAUNCHER, project / LAUNCHER.name)
    (project / 'requirements-lock.txt').touch()
    (project / 'backend' / 'app.py').touch()
    (project / 'scripts' / 'check_approved_ui.py').touch()
    (project / 'scripts' / 'run_phone_demo.py').write_text(
        "import sys\n"
        "assert sys.argv[1:] == ['--full-demo', '--port', '8766']\n"
        "print('DEMO_START_CONFIRMED')\n",
        encoding='utf-8',
    )
    venv.EnvBuilder(with_pip=False).create(project / '.venv-demo')

    result = launch(project)

    assert result.returncode == 0, result.stdout + result.stderr
    assert 'DEMO_START_CONFIRMED' in result.stdout
