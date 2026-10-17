"""Offline regression report verifier; never connects to application databases."""
import argparse
import json
from pathlib import Path


def analyze(data):
    issues = []
    if not isinstance(data, dict):
        return {'valid': False, 'issues': ['root_not_object'], 'passed': 0, 'failed': 0, 'timed_out': 0, 'complete': False}
    groups = data.get('batches')
    if not isinstance(groups, list):
        return {'valid': False, 'issues': ['batches_not_list'], 'passed': 0, 'failed': 0, 'timed_out': 0, 'complete': False}
    passed = failed = timed_out = 0
    seen = set()
    for i, group in enumerate(groups):
        if not isinstance(group, dict):
            issues.append(f'batch_{i}_not_object')
            continue
        number = group.get('batch')
        if type(number) is not int or number < 1 or number in seen:
            issues.append(f'batch_{i}_invalid_number')
        else:
            seen.add(number)
        files = group.get('files')
        if not isinstance(files, list) or not files or not all(isinstance(f, str) and f.startswith('test_') and f.endswith('.py') and '/' not in f and '\\' not in f for f in files):
            issues.append(f'batch_{i}_invalid_files')
        rc = group.get('returncode')
        if rc is None and group.get('timeout') is True:
            timed_out += 1
        elif type(rc) is int and rc == 0:
            passed += 1
        elif type(rc) is int:
            failed += 1
        else:
            issues.append(f'batch_{i}_invalid_result')
        seconds = group.get('seconds')
        if type(seconds) not in (int, float) or seconds < 0 or seconds != seconds:
            issues.append(f'batch_{i}_invalid_duration')
    complete = data.get('complete') is True
    if type(data.get('complete')) is not bool:
        issues.append('invalid_complete_flag')
    if complete and (failed or timed_out or issues or not groups):
        issues.append('false_complete_claim')
    if complete and seen != set(range(1, len(groups) + 1)):
        issues.append('non_contiguous_complete_batches')
    if complete and (data.get('start_batch') != 1 or data.get('only_batch') is not None):
        issues.append('partial_run_claimed_complete')
    return {'valid': not issues, 'issues': issues, 'passed': passed, 'failed': failed, 'timed_out': timed_out, 'complete': complete and not issues}


def main(argv=None):
    parser = argparse.ArgumentParser(description='Offline verification of regression JSON reports')
    parser.add_argument('report', type=Path)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    try:
        data = json.loads(args.report.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        result = {'valid': False, 'issues': [f'unreadable_report:{type(exc).__name__}'], 'passed': 0, 'failed': 0, 'timed_out': 0, 'complete': False}
    else:
        result = analyze(data)
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(f"Valid: {result['valid']}; complete: {result['complete']}; passed batches: {result['passed']}; failed: {result['failed']}; timed out: {result['timed_out']}")
        for issue in result['issues']:
            print('ISSUE:', issue)
    return 0 if result['valid'] and result['complete'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
