"""Wylicz plan ruchu dla polskiej WiejskaPaki bez wykonywania HTTP.

Użycie: python scripts/plan_http_load.py --buyers 5000 --requests-per-buyer 20
Nie łączy się z serwerem ani bazą. Wynik nie potwierdza przepustowości.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.capacity_targets import CapacityTarget, planning_report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sellers", type=int, default=50)
    parser.add_argument("--buyers", type=int, default=5000)
    parser.add_argument("--requests-per-buyer", type=int, default=20)
    parser.add_argument("--peak-hour-percent", type=int, default=20)
    args = parser.parse_args(argv)
    try:
        target = CapacityTarget(
            sellers=args.sellers,
            buyers_per_day=args.buyers,
            page_requests_per_buyer=args.requests_per_buyer,
            buyers_peak_hour_fraction_percent=args.peak_hour_percent,
        )
    except ValueError as exc:
        parser.error(str(exc))
    result = planning_report(target)
    result["estimated_peak_hour_requests"] = target.peak_hour_requests
    result["benchmark_executed"] = False
    result["database_tested"] = False
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
