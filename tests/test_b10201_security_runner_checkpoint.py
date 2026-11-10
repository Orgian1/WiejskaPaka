"""A passing checkpoint must never silently survive changed application or test code."""
import hashlib
from pathlib import Path
from scripts.run_security_focus_isolated import ROOT, fingerprint, FINGERPRINT_PATHS


def test_fingerprint_includes_test_and_backend_sources():
    target = 'tests/test_b10201_security_runner_checkpoint.py'
    actual = fingerprint(target)
    h = hashlib.sha256()
    for path in [ROOT / target, *FINGERPRINT_PATHS]:
        h.update(str(path.relative_to(ROOT)).encode())
        h.update(path.read_bytes() if path.is_file() else b'MISSING')
    assert actual == h.hexdigest()
    assert len(actual) == 64


def test_different_test_files_have_different_fingerprints():
    assert fingerprint('tests/test_b10201_security_runner_checkpoint.py') != fingerprint('tests/test_b8401_shipment_http_idor.py')
