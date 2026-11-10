"""Run from project root: python -m scripts.release_gate"""
import json
from backend.release_readiness import default_report

if __name__ == '__main__':
    print(json.dumps(default_report(), indent=2, ensure_ascii=False))
    raise SystemExit(0 if default_report()['production_ready'] else 2)
