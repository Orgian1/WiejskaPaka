"""Raport planistyczny nie może przedstawiać szacunków jako testów wydajności."""
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CapacityReportCliTests(unittest.TestCase):
    def test_report_is_valid_json_and_not_production_certificate(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "report_capacity_target.py")],
            cwd=str(ROOT), capture_output=True, text=True, timeout=20,
            check=True,
        )
        report = json.loads(result.stdout)
        self.assertEqual(report["first_target"]["sellers"], 50)
        self.assertEqual(report["first_target"]["buyers_per_day"], 5000)
        self.assertEqual(report["first_target"]["currency"], "PLN")
        self.assertEqual(report["pilot"]["sellers"], 20)
        self.assertEqual(report['growth_target']['sellers'], 5000)
        self.assertEqual(report['growth_target']['buyers_per_day'], 500000)
        self.assertFalse(report['growth_target']['capacity_verified'])
        self.assertFalse(report["production_ready"])
        self.assertFalse(report["load_test_completed"])
        self.assertFalse(report["first_target"]["capacity_verified"])


if __name__ == "__main__":
    unittest.main()
