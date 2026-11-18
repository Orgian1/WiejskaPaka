"""Real Chromium smoke test for wallet ad timing and seller stars on approved UI."""
import pytest
from tests.test_full_local_demo_browser import full_demo_server
from playwright.sync_api import sync_playwright


@pytest.mark.parametrize('role', ['klient', 'rolnik'])
def test_wallet_ad_by_role_and_catalog_stars(full_demo_server, role):
    url, accounts = full_demo_server
    with sync_playwright() as driver:
        browser = driver.chromium.launch(headless=True, args=['--no-sandbox'])
        try:
            _check_browser(browser, url, accounts, role)
        finally:
            browser.close()


def _check_browser(browser, url, accounts, role):
    page = browser.new_page(viewport={"width": 1280, "height": 844})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(url)
        page.click("#account-nav-link")
        page.fill("#email", accounts[role]["email"])
        page.fill("#password", accounts[role]["password"])
        with page.expect_response("**/auth/login") as login_response:
            page.locator("#auth button[type=submit]").click()
        login = login_response.value
        assert login.status == 200, (
            f"{role} login rejected with HTTP {login.status}; "
            f"body={login.text()[:400]}"
        )
        page.wait_for_function(
            "(email) => document.querySelector('#identity').textContent.includes(email)",
            arg=accounts["klient"]["email"],
        )
        page.click("#wallet-nav-link")
        ad = page.locator("#wallet-ad-dialog")
        ad.wait_for(state="visible", timeout=10000)
        assert ad.locator("button[aria-label='Zamknij reklamę']").is_disabled()
        assert ad.locator("img").count() == 1
        assert ad.locator("img").get_attribute("alt")
        assert ad.locator("[role=timer]").text_content() in ("5", "4")
        page.locator("#wallet-section").wait_for(state="visible", timeout=12000)
        assert ad.count() == 0
        page.click("#panel-nav-link")
        page.click("#wallet-nav-link")
        page.locator("#wallet-section").wait_for(state="visible", timeout=10000)
        assert ad.count() == 0, "Second wallet entry within 30 minutes must not show an ad"
        page.click("#products-nav-link")
        page.locator(".catalog-product[data-product-id]").first.wait_for(timeout=10000)
        page.locator(".catalog-product [data-seller-stars]").first.wait_for(timeout=10000)
        assert not errors
    finally:
        page.close()
