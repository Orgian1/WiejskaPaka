"""Regression contracts for cart navigation and unit-count badges."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CartNavigationAndBadgeTests(unittest.TestCase):
    def test_same_package_button_opens_cart_route(self):
        source = (ROOT / "web" / "same-package.js").read_text(encoding="utf-8")
        self.assertIn("navigateApp('cart')", source)
        self.assertIn("await loadCart()", source)
        self.assertNotIn("el('cart-section').scrollIntoView", source)

    def test_backend_badge_sums_quantities(self):
        source = (ROOT / "backend" / "navigation_counts.py").read_text(encoding="utf-8")
        self.assertIn("COALESCE(SUM(quantity),0)", source)
        self.assertNotIn("COUNT(*) AS n FROM saved_cart_items", source)

    def test_client_cart_badge_sums_quantities(self):
        source = (ROOT / "web" / "app-views.js").read_text(encoding="utf-8")
        self.assertIn("cartQuoteItems.reduce((total,item)=>total+item.quantity,0)", source)
        self.assertIn("setNavigationCount('cart-count',count", source)


if __name__ == "__main__":
    unittest.main()
