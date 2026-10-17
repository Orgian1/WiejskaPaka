from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from run_full_regression import select_modules


def test_shards_cover_every_test_once():
    root = Path(__file__).resolve().parents[1]
    all_files = select_modules(root)
    shards = [select_modules(root, i, 4) for i in range(1, 5)]
    assert sorted(p for group in shards for p in group) == all_files
    assert len(set(p for group in shards for p in group)) == len(all_files)


def test_bad_shard_rejected():
    for index, count in [(0, 4), (5, 4), (1, 0), (1, -1)]:
        with pytest.raises(ValueError):
            select_modules(shard_index=index, shard_count=count)


def test_empty_tests_fail_closed(tmp_path):
    (tmp_path / 'tests').mkdir()
    with pytest.raises(ValueError, match='No test'):
        select_modules(tmp_path)
