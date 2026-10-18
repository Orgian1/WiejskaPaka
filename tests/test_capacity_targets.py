"""Testy kontraktu planowania obciążenia; bez fikcyjnych wyników benchmarku."""
import unittest

from backend.capacity_targets import CapacityTarget, FIRST_TARGET, PILOT, planning_report


class CapacityTargetsTests(unittest.TestCase):
    def test_first_target_is_poland_only(self):
        self.assertEqual((FIRST_TARGET.market, FIRST_TARGET.currency), ("PL", "PLN"))
        self.assertEqual((FIRST_TARGET.sellers, FIRST_TARGET.buyers_per_day), (50, 5000))

    def test_peak_estimate_is_explicit_assumption_not_capacity_proof(self):
        result = planning_report()
        self.assertEqual(result["estimated_requests_per_day"], 100000)
        self.assertEqual(result["estimated_peak_requests_per_second"], 6)
        self.assertIs(result["capacity_verified"], False)

    def test_pilot_is_smaller(self):
        self.assertLess(PILOT.requests_per_day, FIRST_TARGET.requests_per_day)

    def test_other_markets_or_currencies_are_not_accepted(self):
        for kwargs in ({"market": "DE"}, {"currency": "EUR"}, {"market": "de"}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    CapacityTarget(**kwargs)

    def test_invalid_sizes_are_rejected(self):
        for kwargs in ({"sellers": 0}, {"buyers_per_day": -1},
                       {"page_requests_per_buyer": 0},
                       {"buyers_peak_hour_fraction_percent": 101},
                       {"buyers_peak_hour_fraction_percent": 0},
                       {"buyers_per_day": True}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    CapacityTarget(**kwargs)


if __name__ == "__main__":
    unittest.main()
