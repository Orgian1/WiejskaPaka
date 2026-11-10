"""Wypisz jawne założenia skali polskiej WiejskaPaki jako JSON.

To kalkulator planistyczny, NIE benchmark ani dowód gotowości produkcyjnej.
Uruchom z katalogu repozytorium: python scripts/report_capacity_target.py
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.capacity_targets import FIRST_TARGET, GROWTH_TARGET, PILOT, planning_report


def main():
    result = {
        "pilot": planning_report(PILOT),
        "first_target": planning_report(FIRST_TARGET),
        "growth_target": planning_report(GROWTH_TARGET),
        "production_ready": False,
        "load_test_completed": False,
        "warning": "Nie przeprowadzono pomiaru HTTP/PostgreSQL na docelowym serwerze.",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
