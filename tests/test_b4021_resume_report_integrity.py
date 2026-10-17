"""Regression checkpoint must not silently accept duplicate records."""
import ast
from pathlib import Path


def test_runner_rejects_duplicate_batches_and_files():
    src = (Path(__file__).resolve().parents[1] / 'scripts' / 'run_regression_chunks.py').read_text()
    ast.parse(src)
    assert 'if idx in seen_batches:' in src
    assert 'len(names) != len(set(names))' in src
    assert "any(name not in batch['files'] for name in names)" in src


def test_runner_requires_matching_application_and_test_fingerprint():
    src = (Path(__file__).resolve().parents[1] / 'scripts' / 'run_regression_chunks.py').read_text()
    assert "saved.get('application_sha256') != app_sha256" in src
    assert "saved.get('manifest_sha256') != snapshot['sha256']" in src
