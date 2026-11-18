"""Pickup point map usability and honest demo billing contract."""
import unittest
from pathlib import Path


class PickupMapUsabilityTests(unittest.TestCase):
    def test_street_map_button_precedes_canvas(self):
        source=(Path(__file__).resolve().parents[1]/'web'/'pickup-map.js').read_text(encoding='utf-8')
        self.assertIn('search,open,gps,results,tiles,canvas,center,status',source)
        self.assertIn('Włącz szczegółową mapę ulic (OpenStreetMap)',source)
        self.assertIn('tile.openstreetmap.org',source)
        self.assertIn("tiles.onclick=()=>act(async()=>",source)

    def test_demo_does_not_pretend_to_charge(self):
        source=(Path(__file__).resolve().parents[1]/'web'/'pickup-promotions.js').read_text(encoding='utf-8')
        self.assertIn('Demo nie nalicza opłat za pozostałe punkty',source)


if __name__=='__main__':
    unittest.main()
