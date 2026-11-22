"""Real Chromium smoke test for wallet ad timing and seller stars on approved UI."""
import pytest
from tests.test_full_local_demo_browser import close_login_guide, full_demo_server
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
        titles = {
            "buyer": "Kampania kupujących",
            "seller": "Kampania sprzedawcy",
            "login": "Oferta dla klientów przed logowaniem" if role == "rolnik" else None,
        }

        def show_campaign(route):
            title = titles[route.request.url.rsplit("/", 1)[-1]]
            route.fulfill(json={
                "campaign": {"title": title, "body": "Oferta sezonowa"} if title else None
            })

        page.route("**/ads/slots/*", show_campaign)
        page.goto(url)
        page.click("#header-login-link")
        login_ad = page.locator('#tresc > [data-ad-slot="login"]')
        expect(login_ad).to_be_visible()
        artwork = login_ad.get_by_role("img", name="Zareklamuj się na WiejskaPaka", exact=False)
        if role == "rolnik":
            expect(login_ad.locator("strong")).to_have_text("Oferta dla klientów przed logowaniem")
            expect(artwork).to_have_count(0)
        else:
            expect(artwork).to_be_visible()
            page.wait_for_function(
                "() => document.querySelector('.wp-login-ad-artwork').naturalWidth === 1672"
            )
        account = page.locator("#account-section")
        reset = page.locator("#password-reset-section")
        expect(reset).to_be_visible()
        left, middle, right = (item.bounding_box() for item in (account, login_ad, reset))
        assert left["x"] + left["width"] <= middle["x"]
        assert middle["x"] + middle["width"] <= right["x"]
        assert left["y"] == middle["y"] == right["y"]
        assert left["width"] == pytest.approx(middle["width"], abs=1)
        login_ad.evaluate("(ad) => { ad.hidden = true; }")
        assert account.bounding_box()["x"] == left["x"]
        assert reset.bounding_box()["x"] == right["x"]
        login_ad.evaluate("(ad) => { ad.hidden = false; }")
        assert page.locator('.wp-ad-slot:visible').count() == 1
        page.set_viewport_size({"width": 390, "height": 844})
        expect(login_ad).to_be_visible()
        mobile_form, mobile_ad = account.bounding_box(), login_ad.bounding_box()
        assert mobile_form["y"] + mobile_form["height"] <= mobile_ad["y"]
        if role == "klient":
            mobile_artwork = artwork.bounding_box()
            assert mobile_artwork["width"] <= mobile_ad["width"]
            assert mobile_artwork["width"] / mobile_artwork["height"] == pytest.approx(1672 / 941, abs=.03)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.set_viewport_size({"width": 1280, "height": 844})
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
        close_login_guide(page)
        expect(login_ad).to_be_hidden()
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
        title = "Kampania kupujących" if role == "klient" else "Kampania sprzedawcy"
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
        expect(side).to_be_visible()
        page.click("#wallet-nav-link")
        page.locator("#wallet-section").wait_for(state="visible", timeout=10000)
        assert ad.count() == 0, "Second wallet entry within 30 minutes must not show an ad"
        routes = ["products", "nearby", "favorites", "orders", "account", "dashboard", "notifications", "contact"]
        routes += ["cart"] if role == "klient" else ["listings"]
        for panel in routes:
            page.evaluate("""async (panel) => {
                navigateApp(panel);
                await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
            }""", panel)
            expect(side).to_be_visible()
            page.wait_for_function("""(slotId) => {
                const ad = document.querySelector('[data-ad-slot="' + slotId + '"][data-layout="side"]');
                if (!ad || ad.hidden) return false;
                const a = ad.getBoundingClientRect();
                return [...document.querySelectorAll('#tresc > section')].every(section => {
                    const b = section.getBoundingClientRect();
                    return !b.width || !b.height || a.right <= b.left + 1 ||
                           a.left >= b.right - 1 || a.bottom <= b.top + 1 || a.top >= b.bottom - 1;
                });
            }""", arg=slot_id, timeout=5000)
            if panel == "dashboard":
                assert side.bounding_box()["x"] > information.bounding_box()["x"], panel
            assert page.locator('.wp-ad-slot:visible').count() == 1, panel
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
            close_login_guide(page)
            page.click("#products-nav-link")
            card = page.locator(".catalog-product[data-product-id]").first
            card.wait_for(timeout=10000)
            card.locator("summary").click()
            product_id = card.get_attribute("data-product-id")
            details = page.locator("#catalog-details-" + product_id)
            details.locator('input[aria-label^="Ilość w jednostce"]').fill("3")
            details.get_by_role("button", name="Dodaj do koszyka").click()
            dialog = page.get_by_role("dialog", name="Dobierz do jednej paczki od tego sprzedawcy")
            dialog.wait_for(state="visible", timeout=10000)
            page.locator("#same-package-done").click()
            page.wait_for_url("**/#cart")
            page.locator("#cart-section").wait_for(state="visible")
            page.wait_for_function(
                "() => document.querySelector('#cart-count')?.textContent.trim()==='3'"
            )
        finally:
            browser.close()


def test_seller_confirms_arrival_for_the_point(full_demo_server):
    url, accounts = full_demo_server
    with sync_playwright() as driver:
        browser = driver.chromium.launch(headless=True, args=['--no-sandbox'])
        page = browser.new_page(
            geolocation={"latitude": 51.21, "longitude": 16.16, "accuracy": 10},
            permissions=["geolocation"],
        )
        try:
            page.goto(url)
            page.click("#header-login-link")
            page.fill("#email", accounts["rolnik"]["email"])
            page.fill("#password", accounts["rolnik"]["password"])
            page.locator("#auth button[type=submit]").click()
            close_login_guide(page)
            page.click("#panel-nav-link")
            arrival_panel = page.locator("#dashboard-content > [data-dashboard-pickup-arrival]")
            button = arrival_panel.get_by_role("button", name="Jestem na miejscu")
            expect(button).to_be_visible()
            assert arrival_panel.evaluate("(panel) => panel === panel.parentElement.firstElementChild")
            page.click("#points-nav-link")
            column = page.locator("#points-arrival-column")
            button = column.get_by_role("button", name="Jestem na miejscu")
            ad = column.locator('[data-ad-slot="seller"]')
            expect(button).to_be_visible()
            expect(ad).to_be_visible()
            assert page.locator(".wp-ad-slot:visible").count() == 1
            panel_box, ad_box, profile_box, editor_box = (
                locator.bounding_box() for locator in (
                    column.locator("section"), ad, page.locator("#farmer-details"),
                    page.locator("#point-location-panel"),
                )
            )
            assert panel_box["y"] == profile_box["y"] == editor_box["y"]
            assert panel_box["x"] == ad_box["x"] < profile_box["x"] < editor_box["x"]
            assert panel_box["y"] + panel_box["height"] <= ad_box["y"]
            page.set_viewport_size({"width": 390, "height": 844})
            assert button.bounding_box()["y"] < ad.bounding_box()["y"]
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            with page.expect_response("**/pickup-points/*/arrival") as response:
                button.click()
            assert response.value.status == 200
            expect(column.get_by_role("status")).to_contain_text("Ostatnie potwierdzenie przybycia")
            page.click("#panel-nav-link")
            expect(arrival_panel.get_by_role("status")).to_contain_text("Ostatnie potwierdzenie przybycia")
            page.click("#orders-nav-link")
            group = page.locator(".seller-pickup-group").first
            group.locator("summary").first.click()
            expect(group.get_by_role("button", name="Jestem na miejscu")).to_be_visible()
            assert group.get_by_role("button", name="Gotowe do odbioru (test)", exact=True).count() == 0
        finally:
            browser.close()
