"""Offline manifest and safe path validation for isolated regression runs."""
from pathlib import Path
import hashlib
import json


def discover(root):
    root = Path(root).resolve()
    directory = (root / 'tests').resolve()
    if not directory.is_dir() or not directory.is_relative_to(root):
        raise ValueError('Invalid tests directory')
    result = []
    for candidate in sorted(directory.glob('test_*.py')):
        if candidate.is_symlink() or not candidate.is_file() or candidate.resolve().parent != directory:
            raise ValueError(f'Unsafe test file: {candidate.name}')
        result.append(candidate)
    if not result:
        raise ValueError('No tests discovered')
    return result


def manifest(root):
    root = Path(root).resolve()
    entries = []
    for path in discover(root):
        entries.append({'file': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size})
    canonical = json.dumps(entries, sort_keys=True, separators=(',', ':')).encode()
    return {'format': 1, 'count': len(entries), 'files': entries, 'sha256': hashlib.sha256(canonical).hexdigest()}


def verify(root, expected):
    actual = manifest(root)
    return actual == expected


def application_fingerprint(root):
    """Hash executable sources to invalidate stale resumed chunk results."""
    root = Path(root).resolve()
    digest = hashlib.sha256()
    for folder in ('backend', 'web', 'database', 'scripts'):
        base = root / folder
        if not base.is_dir():
            continue
        for path in sorted(base.rglob('*')):
            if path.is_file() and path.suffix in ('.py', '.js', '.sql', '.html', '.css'):
                digest.update(path.relative_to(root).as_posix().encode('utf-8'))
                digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()
