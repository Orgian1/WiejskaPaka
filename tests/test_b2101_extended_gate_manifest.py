"""Contract tests for the extended offline release gate."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('extended_gate', ROOT / 'scripts' / 'run_extended_release_gate.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_extended_gate_has_unique_modules_in_multiple_domains():
    files = module.selected_files(ROOT)
    assert len(files) >= 20
    assert len(files) == len(set(files))
    assert len(module.GROUPS) >= 4
    assert all(path.parent == ROOT / 'tests' for path in files)


def test_extended_gate_fails_closed_when_modules_missing(tmp_path):
    (tmp_path / 'tests').mkdir()
    try:
        module.selected_files(tmp_path)
    except FileNotFoundError as exc:
        assert 'Missing required modules' in str(exc)
    else:
        raise AssertionError('Missing modules should prevent a successful gate')
