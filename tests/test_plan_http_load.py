"""CLI szacowania ruchu: bez połączeń sieciowych i fikcyjnych pomiarów."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "plan_http_load.py"


class HttpLoadPlanningTests(unittest.TestCase):
    def invoke(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=ROOT,
                              text=True, capture_output=True, timeout=15)

    def test_default_target(self):
        proc = self.invoke()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        report = json.loads(proc.stdout)
        self.assertEqual(report["estimated_peak_hour_requests"], 20000)
        self.assertEqual(report["estimated_peak_requests_per_second"], 6)
        self.assertEqual((report["market"], report["currency"]), ("PL", "PLN"))
        self.assertFalse(report["benchmark_executed"])
        self.assertFalse(report["database_tested"])

    def test_custom_target(self):
        proc = self.invoke("--sellers", "20", "--buyers", "1000",
                           "--requests-per-buyer", "10", "--peak-hour-percent", "30")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        report = json.loads(proc.stdout)
        self.assertEqual(report["estimated_peak_hour_requests"], 3000)
        self.assertEqual(report["estimated_peak_requests_per_second"], 1)

    def test_invalid_arguments_fail(self):
        for args in (("--buyers", "0"), ("--sellers", "-2"),
                     ("--peak-hour-percent", "101"), ("--requests-per-buyer", "0")):
            with self.subTest(args=args):
                self.assertNotEqual(self.invoke(*args).returncode, 0)


if __name__ == "__main__":
    unittest.main()
