"""Summarize checkpointed per-file regression evidence without claiming completion."""
import argparse
import json
from pathlib import Path


def summarize(report):
    batches = report.get('batches', [])
    if not isinstance(batches, list):
        raise ValueError('Invalid batches')
    passed = failed = timed_out = 0
    seen = set()
    for batch in batches:
        if not isinstance(batch, dict) or not isinstance(batch.get('file_results'), list):
            raise ValueError('Invalid batch')
        for item in batch['file_results']:
            name = item.get('file')
            if not isinstance(name, str) or name in seen:
                raise ValueError('Duplicate or invalid test module')
            seen.add(name)
            if item.get('timeout') is True:
                timed_out += 1
            elif item.get('returncode') == 0 and type(item.get('returncode')) is int:
                passed += 1
            else:
                failed += 1
    return {'modules_seen': len(seen), 'passed': passed, 'failed': failed,
            'timed_out': timed_out, 'complete': report.get('complete') is True,
            'in_progress': any(b.get('in_progress') is True for b in batches)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('report', type=Path)
    args = parser.parse_args()
    print(json.dumps(summarize(json.loads(args.report.read_text(encoding='utf-8'))), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
