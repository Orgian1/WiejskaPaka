"""Run pytest in isolated batches, keeping a report even on timeout/failure.

No production database is ever passed to child processes.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

from run_tests_isolated import test_environment
from regression_manifest import discover, manifest
from regression_manifest import application_fingerprint


def batches(files, size):
    if size < 1:
        raise ValueError('batch size must be positive')
    return [files[i:i + size] for i in range(0, len(files), size)]


def write_report_atomic(path, payload):
    """Avoid leaving a truncated JSON report after interruption."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=destination.parent,
                                         prefix='.regression_', suffix='.tmp', delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def run(root, *, batch_size=12, timeout=90, report=None, selected=None, start_batch=1, stop_on_failure=False, only_batch=None, resume=False):
    root = Path(root).resolve()
    if timeout <= 0:
        raise ValueError('timeout must be positive')
    if selected is None:
        files = discover(root)
        snapshot = manifest(root)
    else:
        files = sorted(Path(p) for p in selected)
        # Explicitly selected tests may live in pytest's temporary directory.
        # This is needed for regression tests of the runner itself. Never
        # accept symlinked test files or non-test Python files.
        if any(p.is_symlink() or not p.is_file()
               or not p.name.startswith('test_') or p.suffix != '.py' for p in files):
            raise ValueError('Selected tests must be regular test_*.py files')
        files = [p.resolve() for p in files]
        import hashlib
        import json as _json
        entries = [{'file': str(p.relative_to(root) if p.is_relative_to(root) else p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]
        snapshot = {'sha256': hashlib.sha256(_json.dumps(entries, sort_keys=True).encode()).hexdigest(), 'count': len(files)}
    app_sha256 = application_fingerprint(root)
    if not files:
        raise ValueError('No test files found')
    if only_batch is not None and only_batch < 1:
        raise ValueError('only_batch must be positive')
    if start_batch < 1:
        raise ValueError("start_batch must be positive")
    groups = batches(files, batch_size)
    if start_batch > len(groups) or (only_batch is not None and only_batch > len(groups)):
        raise ValueError('requested batch exceeds available batches')
    previous = {}
    if resume and report and Path(report).exists():
        saved = json.loads(Path(report).read_text(encoding='utf-8'))
        if saved.get('application_sha256') != app_sha256:
            raise ValueError('Nie można wznowić: zmieniono kod aplikacji; wymagane nowe uruchomienie')
        if saved.get('manifest_sha256') != snapshot['sha256'] or saved.get('manifest_count') != snapshot['count']:
            raise ValueError('Nie można wznowić: zmieniono zestaw testów; wymagane nowe uruchomienie')
        if saved.get('only_batch') != only_batch or saved.get('start_batch') != start_batch:
            raise ValueError('Nie można wznowić: inny zakres grup testowych')
        seen_batches = set()
        for batch in saved.get('batches', []):
            idx = batch.get('batch')
            if not isinstance(idx, int) or idx < 1 or idx > len(groups):
                raise ValueError('Nieprawidłowy numer grupy w raporcie')
            if idx in seen_batches:
                raise ValueError('Nie można wznowić: powtórzona grupa w raporcie')
            seen_batches.add(idx)
            if batch.get('files') != [p.name for p in groups[idx - 1]]:
                raise ValueError('Nie można wznowić: niezgodne pliki w raporcie')
            records = batch.get('file_results', [])
            names = [r.get('file') for r in records]
            if len(names) != len(set(names)) or any(name not in batch['files'] for name in names):
                raise ValueError('Nie można wznowić: powtórzony lub obcy plik w raporcie')
            previous[idx] = {r['file']: r for r in records if r.get('returncode') == 0}
    results = []
    for index, group in enumerate(groups, 1):
        if (only_batch is not None and index != only_batch) or (only_batch is None and index < start_batch):
            continue
        # Each test module gets a fresh database and Python interpreter. A shared
        # database across modules produced false failures in the full regression.
        file_results = []
        batch_started = time.monotonic()
        for test_file in group:
            if test_file.name in previous.get(index, {}):
                file_results.append(previous[index][test_file.name])
                continue
            with tempfile.TemporaryDirectory(prefix='wiejskapaka_file_') as tmp:
                env = test_environment(os.environ, Path(tmp) / 'isolated.sqlite3')
                command = [sys.executable, '-m', 'pytest', '-q', '--disable-warnings', str(test_file)]
                started = time.monotonic()
                try:
                    completed = subprocess.run(command, cwd=root, env=env, capture_output=True,
                                               text=True, encoding='utf-8', timeout=timeout)
                    item = {'file': test_file.name, 'returncode': completed.returncode,
                            'seconds': round(time.monotonic() - started, 2),
                            'output_tail': (completed.stdout + completed.stderr)[-2500:]}
                except subprocess.TimeoutExpired as exc:
                    stdout = exc.stdout.decode('utf-8', 'replace') if isinstance(exc.stdout, bytes) else (exc.stdout or '')
                    stderr = exc.stderr.decode('utf-8', 'replace') if isinstance(exc.stderr, bytes) else (exc.stderr or '')
                    item = {'file': test_file.name, 'returncode': None, 'timeout': True,
                            'seconds': round(time.monotonic() - started, 2),
                            'output_tail': (stdout + stderr)[-2500:]}
            file_results.append(item)
            if report:
                # Checkpoint progress even if the run is interrupted mid-batch.
                partial = {'batch': index, 'files': [p.name for p in group],
                           'returncode': None, 'seconds': round(time.monotonic() - batch_started, 2),
                           'file_results': file_results, 'in_progress': True}
                write_report_atomic(report, {'complete': False, 'start_batch': start_batch,
                                    'only_batch': only_batch, 'batches': results + [partial],
                                    'application_sha256': app_sha256, 'manifest_sha256': snapshot['sha256'],
                                    'manifest_count': snapshot['count']})
        failures = [item for item in file_results if item['returncode'] != 0]
        entry = {'batch': index, 'files': [p.name for p in group],
                 'returncode': 0 if not failures else 1,
                 'seconds': round(time.monotonic() - batch_started, 2),
                 'file_results': file_results,
                 'timeout': any(item.get('timeout', False) for item in file_results),
                 'output_tail': '\n'.join(item['file'] + ': ' + item['output_tail'][-500:]
                                          for item in failures)[-5000:]}
        results.append(entry)
        print(f"Batch {index}: {'PASS' if entry['returncode'] == 0 else 'INCOMPLETE/FAIL'} ({entry['seconds']}s)", flush=True)
        if report:
            write_report_atomic(report, {'complete': False, 'start_batch': start_batch, 'only_batch': only_batch, 'batches': results, 'application_sha256': app_sha256, 'manifest_sha256': snapshot['sha256'], 'manifest_count': snapshot['count']})
        if stop_on_failure and entry['returncode'] != 0:
            break
    success = all(entry['returncode'] == 0 for entry in results)
    complete = success and start_batch == 1 and only_batch is None and len(results) == len(groups)
    if report:
        write_report_atomic(report, {'complete': complete, 'start_batch': start_batch, 'only_batch': only_batch, 'batches': results, 'application_sha256': app_sha256, 'manifest_sha256': snapshot['sha256'], 'manifest_count': snapshot['count']})
    return 0 if success else 1  # Partial runs are successful only for their selected scope; see report.complete.


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--batch-size', type=int, default=12)
    parser.add_argument('--timeout', type=int, default=90)
    parser.add_argument('--report', default='regression_batches_report.json')
    parser.add_argument('--start-batch', type=int, default=1)
    parser.add_argument('--stop-on-failure', action='store_true')
    parser.add_argument('--only-batch', type=int, default=None)
    parser.add_argument('--list-batches', action='store_true')
    parser.add_argument('--resume', action='store_true', help='Wznów zaliczone moduły z aktualnego raportu')
    args = parser.parse_args()
    if args.timeout < 1 or args.batch_size < 1 or args.start_batch < 1:
        parser.error('timeout and batch-size must be positive')
    root = Path(__file__).resolve().parents[1]
    if args.list_batches:
        groups = batches(sorted((root / 'tests').glob('test_*.py')), args.batch_size)
        for index, group in enumerate(groups, 1):
            print(f'Batch {index}: {len(group)} files: {group[0].name} ... {group[-1].name}')
        return 0
    return run(root, batch_size=args.batch_size, timeout=args.timeout, report=args.report, start_batch=args.start_batch, stop_on_failure=args.stop_on_failure, only_batch=args.only_batch, resume=args.resume)


if __name__ == '__main__':
    raise SystemExit(main())
