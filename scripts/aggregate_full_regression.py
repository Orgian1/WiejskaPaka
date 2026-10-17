"""Combine regression shard reports; reject incomplete, stale or duplicated coverage."""
import argparse
import json
from pathlib import Path
from scripts.regression_manifest import manifest
import os
import tempfile


def write_report_atomic(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        tmp = handle.name
    os.replace(tmp, path)


def aggregate(root, report_paths):
    root = Path(root).resolve()
    expected_hashes = {item["file"]: item["sha256"] for item in manifest(root)["files"]}
    expected = set(expected_hashes)
    seen = set()
    failures = []
    shards = []
    for path in report_paths:
        data = json.loads(Path(path).read_text(encoding='utf-8'))
        entries = data.get('results', [])
        if not isinstance(entries, list) or not data.get('complete') or data.get('executed') != len(entries) or data.get('planned') != len(entries):
            raise ValueError(f'Incomplete or invalid shard report: {path}')
        local = set()
        for entry in entries:
            name = entry.get('file')
            if not isinstance(name, str) or name not in expected:
                raise ValueError(f'Unknown module in {path}: {name}')
            if entry.get('sha256') != expected_hashes[name]:
                raise ValueError(f'Stale or missing test checksum in {path}: {name}')
            if name in seen or name in local:
                raise ValueError(f'Duplicate module: {name}')
            local.add(name)
            if entry.get('returncode') != 0:
                failures.append(name)
        seen.update(local)
        shards.append({'report': Path(path).name, 'modules': len(entries)})
    missing = sorted(expected - seen)
    return {'complete': not missing, 'success': not missing and not failures,
            'expected': len(expected), 'executed': len(seen), 'passed': len(seen) - len(failures),
            'failed': len(failures), 'missing': missing, 'failures': sorted(failures), 'shards': shards}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reports', nargs='+')
    parser.add_argument('--output', default='full_regression_summary.json')
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    try:
        summary = aggregate(root, args.reports)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    write_report_atomic(root / args.output, summary)
    print(f"Modules: {summary['passed']}/{summary['expected']} passed; missing: {len(summary['missing'])}; failed: {summary['failed']}")
    return 0 if summary['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
