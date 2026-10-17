import json
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from regression_manifest import discover, manifest, verify
from run_regression_chunks import run


def setup(tmp_path):
    d = tmp_path / 'tests'
    d.mkdir()
    (d / 'test_one.py').write_text('def test_ok(): assert True\n')
    return d


def test_manifest_is_stable(tmp_path):
    setup(tmp_path)
    assert manifest(tmp_path) == manifest(tmp_path)


def test_manifest_has_digest(tmp_path):
    setup(tmp_path)
    assert len(manifest(tmp_path)['sha256']) == 64


def test_manifest_detects_modified_test(tmp_path):
    d = setup(tmp_path)
    m = manifest(tmp_path)
    (d / 'test_one.py').write_text('def test_ok(): assert False\n')
    assert not verify(tmp_path, m)


def test_manifest_detects_added_test(tmp_path):
    d = setup(tmp_path)
    m = manifest(tmp_path)
    (d / 'test_two.py').write_text('def test_other(): pass\n')
    assert not verify(tmp_path, m)


def test_manifest_detects_removed_test(tmp_path):
    d = setup(tmp_path)
    m = manifest(tmp_path)
    (d / 'test_one.py').unlink()
    with pytest.raises(ValueError):
        verify(tmp_path, m)


def test_symlink_rejected(tmp_path):
    d = setup(tmp_path)
    outside = tmp_path / 'other.py'
    outside.write_text('pass')
    (d / 'test_unsafe.py').symlink_to(outside)
    with pytest.raises(ValueError, match='Unsafe'):
        discover(tmp_path)


def test_missing_tests_rejected(tmp_path):
    with pytest.raises(ValueError):
        discover(tmp_path)


def test_directory_is_rejected(tmp_path):
    d = setup(tmp_path)
    (d / 'test_folder.py').mkdir()
    with pytest.raises(ValueError):
        discover(tmp_path)


def test_manifest_file_size(tmp_path):
    d = setup(tmp_path)
    assert manifest(tmp_path)['files'][0]['bytes'] == (d / 'test_one.py').stat().st_size


def test_runner_rejects_external_selection(tmp_path):
    setup(tmp_path)
    outside = tmp_path / 'external.py'
    outside.write_text('pass')
    with pytest.raises(ValueError, match='Selected tests'):
        run(tmp_path, selected=[outside])


def test_runner_rejects_symlink_selection(tmp_path):
    d = setup(tmp_path)
    outside = tmp_path / 'external.py'
    outside.write_text('pass')
    link = d / 'test_link.py'
    link.symlink_to(outside)
    with pytest.raises(ValueError):
        run(tmp_path, selected=[link])
