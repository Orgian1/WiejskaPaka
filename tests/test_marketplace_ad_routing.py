"""Regression checks for the marketplace ad routing contract."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class MarketplaceAdRoutingTests(unittest.TestCase):
    def test_ad_slots_remain_inside_their_own_sections(self):
        script=(ROOT/'web/app-views.js').read_text(encoding='utf-8')
        self.assertIn('target.append(host);',script)
        self.assertIn("{id:'login',after:'#account-section',roles:['guest']}",script)
        self.assertIn("{id:'seller',after:'#seller-listings-section',roles:['rolnik']}",script)
        self.assertNotIn("{id:'login',after:'#auth'",script)
        self.assertNotIn('target.after(host);',script)
        self.assertIn("document.addEventListener('wiejskapaka:route-changed',refresh);",script)
        self.assertIn("document.dispatchEvent(new Event('wiejskapaka:route-changed'));",script)

    def test_admin_changes_refresh_active_campaigns(self):
        script=(ROOT/'web/app-views.js').read_text(encoding='utf-8')
        self.assertIn("new Event('wiejskapaka:ads-updated')",script)
        self.assertIn("data?.campaign||defaultCampaigns[config.id]",script)
        self.assertIn("cache:'no-store'",script)

    def test_approved_ui_assets_are_not_modified_by_ad_system(self):
        script=(ROOT/'web/app-views.js').read_text(encoding='utf-8')
        self.assertIn("config.id==='login'?route==='account'",script)
        self.assertIn("config.id==='buyer'?route==='nearby':route==='listings'",script)
        self.assertIn("!host.closest('[data-route-hidden]')",script)
        self.assertIn("!host.closest('[hidden]')",script)

if __name__=='__main__':
    unittest.main()
