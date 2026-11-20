"""Regression checks for the marketplace ad routing contract."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class MarketplaceAdRoutingTests(unittest.TestCase):
    def test_ad_slots_remain_inside_their_own_sections(self):
        script=(ROOT/'web/app-views.js').read_text(encoding='utf-8')
        self.assertIn('target.append(host);',script)
        self.assertIn("{id:'login',target:'#account-section',route:'account',role:'guest'}",script)
        self.assertIn("{id:'seller',target:'#seller-listings-section',route:'listings',role:'rolnik'}",script)
        self.assertNotIn("{id:'login',target:'#auth'",script)
        self.assertNotIn('target.after(host);',script)
        self.assertIn("document.addEventListener('wiejskapaka:route-changed',refresh);",script)
        self.assertIn("document.dispatchEvent(new Event('wiejskapaka:route-changed'));",script)

    def test_admin_changes_refresh_active_campaigns(self):
        script=(ROOT/'web/app-views.js').read_text(encoding='utf-8')
        self.assertIn("new Event('wiejskapaka:ads-updated')",script)
        self.assertIn("if(version!==campaignReloadVersion)return;",script)
        self.assertIn("if(!setCampaign('login',campaigns.login))setCampaign('login',campaigns.buyer);",script)
        self.assertIn("cache:'no-store'",script)

    def test_side_slots_use_existing_grid_space_and_external_styles(self):
        script=(ROOT/'web/app-views.js').read_text(encoding='utf-8')
        self.assertIn("mount(config,main,true)",script)
        self.assertIn("routeStatus.getBoundingClientRect()",script)
        self.assertIn("style.href='/assets/marketplace-ads.css'",script)
        self.assertIn("config.route!==appCurrentView",script)
        self.assertIn("host.parentElement.closest('[data-route-hidden], [hidden]')",script)

if __name__=='__main__':
    unittest.main()
