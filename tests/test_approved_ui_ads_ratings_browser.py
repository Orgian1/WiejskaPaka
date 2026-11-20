"""Real Chromium smoke test for wallet ad timing and seller stars on approved UI."""
import pytest
from tests.test_full_local_demo_browser import full_demo_server
from playwright.sync_api import expect, sync_playwright


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
        if role == "rolnik":
            page.route("**/ads/slots/seller", lambda route: route.fulfill(
                json={"campaign": {"title": "Kampania testowa sprzedawcy", "body": "Oferta sezonowa"}}
            ))
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
            arg=accounts[role]["email"],
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
        slot_id = "buyer" if role == "klient" else "seller"
        side = page.locator(f'[data-ad-slot="{slot_id}"][data-layout="side"]')
        expect(side).to_be_visible()
        title = "Miejsce na reklamę" if role == "klient" else "Kampania testowa sprzedawcy"
        expect(side.locator("strong")).to_have_text(title)
        consumer = page.locator("main > section").filter(has=page.get_by_role("heading", name="Prawa konsumenta"))
        information = page.locator("main > section").filter(has=page.get_by_role("heading", name="Informacje", exact=True))
        left, middle, right = (item.bounding_box() for item in (side, consumer, information))
        assert left["x"] < middle["x"] < right["x"]
        assert left["y"] == middle["y"] == right["y"]
        side.evaluate("(element) => { element.hidden = true; }")
        assert (consumer.bounding_box(), information.bounding_box()) == (middle, right)
        side.evaluate("(element) => { element.hidden = false; }")
        expect(side).to_have_css("background-color", "rgb(248, 250, 247)")
        assert page.locator('[data-layout="side"]:visible').count() == 1
        page.set_viewport_size({"width": 390, "height": 844})
        expect(side).to_be_hidden()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.set_viewport_size({"width": 1280, "height": 844})
        page.click("#panel-nav-link")
        expect(side).to_be_hidden()
        page.click("#wallet-nav-link")
        page.locator("#wallet-section").wait_for(state="visible", timeout=10000)
        assert ad.count() == 0, "Second wallet entry within 30 minutes must not show an ad"
        # Seller account has a different product-management view; catalog
        # stars belong to the customer-facing product catalog only.
        if role == "klient":
            page.click("#products-nav-link")
            page.locator(".catalog-product[data-product-id]").first.wait_for(timeout=10000)
            page.locator(".catalog-product [data-seller-stars]").first.wait_for(timeout=10000)
        assert not errors
    finally:
        page.close()


def test_same_package_button_opens_cart_and_badge_counts_units(full_demo_server):
    """A real browser should navigate to cart and count quantities, not lines."""
    url, accounts = full_demo_server
    with sync_playwright() as driver:
        browser = driver.chromium.launch(headless=True, args=['--no-sandbox'])
        page = browser.new_page(viewport={"width": 1280, "height": 844})
        try:
            page.goto(url)
            page.click("#account-nav-link")
            page.fill("#email", accounts["klient"]["email"])
            page.fill("#password", accounts["klient"]["password"])
            with page.expect_response("**/auth/login") as login_response:
                page.locator("#auth button[type=submit]").click()
            assert login_response.value.status == 200
            page.wait_for_function(
                "(email) => document.querySelector('#identity').textContent.includes(email)",
                arg=accounts["klient"]["email"],
            )
            page.click("#products-nav-link")
            card = page.locator(".catalog-product[data-product-id]").first
            card.wait_for(timeout=10000)
            card.locator("summary").click()
            product_id = card.get_attribute("data-product-id")
            details = page.locator("#catalog-details-" + product_id)
            details.locator('input[aria-label^="Ilość w jednostce"]').fill("3")
            details.get_by_role("button", name="Dodaj do koszyka").click()
            dialog = page.locator(".same-package-dialog")
            dialog.wait_for(state="visible", timeout=10000)
            page.locator("#same-package-done").click()
            page.wait_for_url("**/#cart")
            page.locator("#cart-section").wait_for(state="visible")
            page.wait_for_function(
                "() => document.querySelector('#cart-count')?.textContent.trim()==='3'"
            )
        finally:
            browser.close()
