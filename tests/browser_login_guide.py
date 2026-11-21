"""Dismiss the login guide before testing other parts of the app."""


def dismiss_login_guide(page):
    page.locator('#auth').wait_for(state='hidden')
    page.wait_for_function("""() => !['klient','rolnik'].includes(role) ||
        document.getElementById('login-guide')?.open ||
        Number(localStorage.getItem('wp-login-guide-v2:' + role + ':' + checkoutOwner)) >= 5""")
    guide = page.locator('#login-guide[open]')
    if guide.count():
        guide.get_by_role('button').click(timeout=10000)


def stores_only_login_guide_counts(page):
    return page.evaluate(r"""() => Object.entries(localStorage).every(([key, count]) =>
        /^wp-login-guide-v2:(klient|rolnik):\d+$/.test(key) && /^[1-5]$/.test(count))""")
