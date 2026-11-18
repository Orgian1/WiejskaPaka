"""Prevent silent regressions in the approved-layout seller rating extension."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SellerRatingFrontendContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.extension = (ROOT / "web" / "app-views.js").read_text(encoding="utf-8")
        cls.html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        cls.app = (ROOT / "web" / "app.js").read_text(encoding="utf-8")

    def test_extension_loads_after_approved_app(self):
        scripts = re.findall(r'<script[^>]+src="([^"]+)"', self.html)
        self.assertIn("/assets/app.js", scripts)
        self.assertIn("/assets/app-views.js", scripts)
        self.assertLess(scripts.index("/assets/app.js"), scripts.index("/assets/app-views.js"))

    def test_completed_order_detection_uses_actual_status(self):
        self.assertIn(r"/•\s*odebrane(?:\s|$)/", self.extension)
        self.assertIn("box.dataset.orderId=String(o.id)", self.app)

    def test_only_one_submit_handler_and_private_previous_rating_check(self):
        self.assertEqual(self.extension.count("submit.onclick="), 1)
        self.assertIn("submit.disabled=true;", self.extension)
        self.assertIn("api('/seller-ratings/orders/'+orderId)", self.extension)
        self.assertIn("currentEpoch!==sessionEpoch", self.extension)

    def test_failed_previous_rating_lookup_does_not_enable_submit(self):
        self.assertIn("Nie udało się sprawdzić poprzedniej oceny", self.extension)
        self.assertRegex(self.extension, r"\.catch\(\(\)=>\{[\s\S]*?submit\.disabled=true;")

    def test_duplicate_rating_uses_actual_api_error_message(self):
        self.assertIn("To zamówienie zostało już ocenione", self.extension)
        self.assertNotIn("String(error).includes('409')", self.extension)
        self.assertIn("String(error).includes('To zamówienie zostało już ocenione')", self.extension)

    def test_unrated_sellers_show_empty_stars(self):
        self.assertIn("☆☆☆☆☆ (0 ocen)", self.extension)
        self.assertIn("rating.count===0", self.extension)
        self.assertIn("Sprzedawca nie ma jeszcze ocen", self.extension)

    def test_catalog_returns_product_items_to_rating_extension(self):
        # The extension depends on catalogPage returning the same items
        # subsequently rendered by loadProducts, not just a status flag.
        self.assertIn("return data.items;", self.app)
        self.assertIn("const products=await catalogPage(request,epoch)", self.app)
        self.assertIn("const result=await catalogPageBeforeSellerRatings.apply(this,args)", self.extension)
        self.assertIn("if(Array.isArray(result))", self.extension)
        self.assertIn("sellerRatingsByProduct.clear()", self.extension)

    def test_rating_badges_attach_to_existing_product_summary(self):
        self.assertIn("card catalog-product", self.app)
        self.assertIn("const summary=node('summary')", self.app)
        self.assertIn("root.querySelectorAll('.catalog-product[data-product-id]')", self.extension)
        self.assertIn("if(summary)summary.append(stars)", self.extension)

    def test_public_stars_use_actual_product_and_seller_ids(self):
        self.assertIn("box.dataset.productId=String(p.id)", self.app)
        self.assertIn("sellerRatingsByProduct.set(productId,sellerId)", self.extension)
        self.assertIn("api('/sellers/'+sellerId+'/rating')", self.extension)


if __name__ == "__main__":
    unittest.main()
