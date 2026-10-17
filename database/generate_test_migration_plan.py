"""Generate (never execute) a guarded test migration shell script."""
import argparse
from pathlib import Path
from database.test_schema_sequential import build_sequential_plan


def generate(root=None, lock_path=None):
    root = Path(root) if root is not None else Path(__file__).resolve().parent
    result = build_sequential_plan(root, lock_path)
    lines = result['script'].splitlines()
    marker = 'python -m database.validate_migration_target'
    if lines.count(marker) != 1 or lines.count('cd database') != 1:
        raise ValueError('Unexpected migration plan structure')
    # The generated plan can be launched from any working directory; all
    # relative SQL includes remain anchored to the reviewed project tree.
    lines.insert(0, '#!/bin/sh')
    lines.insert(1, '# Run only after manual review, against an empty disposable test DB.')
    lines[lines.index('set -e')] = 'set -eu'
    lines.insert(lines.index(marker), 'python -m database.verify_test_migrations >/dev/null')
    lines.insert(lines.index('python -m database.verify_test_migrations >/dev/null'),
                 'cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)"')
    # Missing tooling must fail before any SQL can be executed.
    lines.insert(lines.index(marker), 'command -v psql >/dev/null 2>&1 || { echo "psql is required" >&2; exit 1; }')
    lines.insert(lines.index('python -m database.verify_test_migrations >/dev/null'), 'command -v python >/dev/null 2>&1 || { echo "python is required" >&2; exit 1; }')
    return '\n'.join(lines) + '\n'



def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    destination = args.output.resolve()
    root = Path(__file__).resolve().parents[1]
    if destination.parent != root:
        parser.error('Output must be in the project root')
    if destination.exists():
        parser.error('Refusing to overwrite an existing plan')
    script = generate()
    import os
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        fd = os.open(destination, flags, 0o600)
    except FileExistsError:
        parser.error('Refusing to overwrite an existing plan')
    with os.fdopen(fd, 'w', encoding='utf-8') as handle:
        handle.write(script)
    print('Offline test plan generated; no SQL executed')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
