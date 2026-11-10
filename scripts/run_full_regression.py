"""Full local regression runner with deterministic sharding and isolated databases.

Run: python scripts/run_full_regression.py --shard 1/4
Then repeat shards 2/4 through 4/4. No network/database credentials forwarded.
"""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from run_tests_per_file import run


def select_modules(root=ROOT, shard_index=1, shard_count=1):
    root = Path(root)
    if shard_count < 1 or not 1 <= shard_index <= shard_count:
        raise ValueError('Shard must have form 1/N through N/N')
    modules = sorted((root / 'tests').glob('test_*.py'))
    if not modules:
        raise ValueError('No test modules found')
    selected = [path for index, path in enumerate(modules) if index % shard_count == shard_index - 1]
    if not selected:
        raise ValueError('Shard has no test modules')
    return selected


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--shard', default='1/1', help='1/4, 2/4, etc.')
    parser.add_argument('--timeout', type=int, default=90)
    parser.add_argument('--resume', action='store_true', help='Reuse passing tests from an interrupted report')
    parser.add_argument('--refresh-stale', action='store_true', help='Re-run changed tests during resume')
    parser.add_argument('--report', default=None)
    args = parser.parse_args(argv)
    try:
        index, count = map(int, args.shard.split('/'))
        modules = select_modules(ROOT, index, count)
        if args.timeout < 1:
            raise ValueError('Timeout must be positive')
    except (ValueError, TypeError) as exc:
        parser.error(str(exc))
    report = ROOT / (args.report or f'full_regression_shard_{index}_of_{count}.json')
    return run(ROOT, selected=modules, timeout=args.timeout, report=report, resume=args.resume, refresh_stale=args.refresh_stale)


if __name__ == '__main__':
    raise SystemExit(main())
