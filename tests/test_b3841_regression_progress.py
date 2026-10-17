import importlib.util
from pathlib import Path
import pytest

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('progress', root / 'scripts' / 'summarize_regression_progress.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_partial_checkpoint_is_not_complete():
    result = module.summarize({'complete': False, 'batches': [{'in_progress': True, 'file_results': [
        {'file': 'test_a.py', 'returncode': 0}, {'file': 'test_b.py', 'returncode': None, 'timeout': True}]}]})
    assert result == {'modules_seen': 2, 'passed': 1, 'failed': 0, 'timed_out': 1, 'complete': False, 'in_progress': True}


def test_duplicate_module_rejected():
    with pytest.raises(ValueError):
        module.summarize({'batches': [{'file_results': [{'file': 'test_a.py'}, {'file': 'test_a.py'}]}]})
