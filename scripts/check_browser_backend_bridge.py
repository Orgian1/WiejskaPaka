"""B/36–40: Chromium UI -> in-process FastAPI TestClient -> disposable SQLite.

The bridge replaces browser fetch (localhost is blocked in some sandboxes).
This is a real backend/API integration test, NOT a real network/HTTP deployment test.
"""
import os
import re
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'web'


def run():
    from playwright.sync_api import sync_playwright
    from fastapi.testclient import TestClient
    from scripts.run_phone_demo import demo_environment

    binary = next((shutil.which(n) for n in ('chromium', 'chromium-browser', 'google-chrome') if shutil.which(n)), None)
    if not binary:
        raise RuntimeError('Chromium is required for the browser/backend bridge test')
    html = (WEB / 'index.html').read_text(encoding='utf-8')
    html = re.sub(r'<script\s+src="/assets/(?:app|dashboard)\.js"\s+defer></script>', '', html)
    html = html.replace('<link rel="stylesheet" href="/assets/style.css">', '')
    with tempfile.TemporaryDirectory(prefix='wiejskapaka_bridge_') as folder:
        # The backend module must be imported only after database isolation.
        os.environ.update(demo_environment(os.environ, Path(folder) / 'integration.sqlite3'))
        from backend.app import app
        with TestClient(app) as client, sync_playwright() as p:
            browser = p.chromium.launch(headless=True, executable_path=binary, args=['--no-sandbox'])
            try:
                page = browser.new_page(viewport={'width': 390, 'height': 844})
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                calls = []

                def bridge(path, method, body, headers):
                    assert isinstance(path, str) and path.startswith('/') and not path.startswith('//'), path
                    method = str(method).upper()
                    assert method in ('GET', 'POST', 'PUT', 'PATCH', 'DELETE'), method
                    response = client.request(method, path, json=body, headers=headers)
                    calls.append((method, path, response.status_code))
                    try:
                        payload = response.json()
                    except ValueError:
                        payload = {'detail': 'Odpowiedź serwera nie jest JSON'}
                    return {'ok': response.is_success, 'status': response.status_code, 'data': payload}

                page.set_content(html)
                page.add_style_tag(content=(WEB / 'style.css').read_text(encoding='utf-8'))
                page.expose_function('__apiBridge', bridge)
                page.evaluate('''() => {
                  window.fetch = async (path, options={}) => {
                    const body = options.body === undefined ? null : JSON.parse(options.body);
                    const result = await window.__apiBridge(String(path), options.method || 'GET', body, options.headers || {});
                    return {ok:result.ok, status:result.status, json:async()=>result.data};
                  };
                }''')
                # about:blank is not a secure context; HTTPS normally provides crypto.randomUUID.
                # Polyfill only the browser test harness, not the application.
                page.evaluate("() => { if (!crypto.randomUUID) crypto.randomUUID = () => 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => { const r = crypto.getRandomValues(new Uint8Array(1))[0] & 15; return (c === 'x' ? r : (r & 3 | 8)).toString(16); }); }")
                for name in ('app.js', 'dashboard.js'):
                    page.add_script_tag(content=(WEB / name).read_text(encoding='utf-8'))
                password = 'TestoweHaslo_123456789'

                def credentials(role):
                    page.locator('#email').fill(f'bridge-{role}@example.invalid')
                    page.locator('#password').fill(password)

                def login(role):
                    credentials(role)
                    page.locator('#auth button[type=submit]').click()
                    page.wait_for_function('(r)=>document.querySelector("#identity").textContent.includes("("+r+")")', arg=role)

                def logout():
                    page.locator('#logout').click()
                    page.wait_for_function('document.querySelector("#identity").textContent === "Nie zalogowano"')
                    assert page.locator('#dashboard').is_hidden()
                    assert page.locator('#orders-section').is_hidden()

                # B/36: actual registration/login through browser and API.
                for role in ('rolnik', 'klient'):
                    credentials(role)
                    page.locator('#role').select_option(role)
                    page.locator('#register').click()
                    page.wait_for_function('(r)=>document.querySelector("#notice").textContent.toLowerCase().includes("zarejestrow") || document.querySelector("#notice").textContent.toLowerCase().includes("utworzon")', arg=role)
                    login(role)
                    logout()
                print('B/36 browser -> FastAPI: registration, login, logout OK')

                # B/37: farmer creates real product and pickup point.
                login('rolnik')
                page.locator('#pname').fill('Marchew integracyjna')
                page.locator('#price').fill('3,49')
                page.locator('#delivery').fill('5,01')
                page.locator('#stock').fill('3')
                page.locator('#new-product button').click()
                page.wait_for_function('document.querySelector("#products").textContent.includes("Marchew integracyjna")')
                page.locator('#point-name').fill('Punkt testowy')
                page.locator('#point-city').fill('Radom')
                page.locator('#point-street').fill('Polna 2')
                page.locator('#point-hours').fill('8-16')
                page.locator('#point-form button').click()
                page.wait_for_function('document.querySelector("#my-points").textContent.includes("Punkt testowy")')
                logout()
                print('B/37 browser -> FastAPI: product and pickup point OK')

                # B/38: pickup order with exact integer-grosz amount.
                login('klient')
                page.wait_for_function('document.querySelector("#products").textContent.includes("Marchew integracyjna")')
                page.wait_for_function('document.querySelectorAll("#products select").length >= 2 && [...document.querySelectorAll("#products select")].some(x => x.getAttribute("aria-label") === "Punkt odbioru" && x.options.length > 0)')
                page.locator('#products button', has_text='Zamów testowo').first.click()
                try:
                    page.wait_for_function('document.querySelector("#notice").textContent.includes("PIN TESTOWY")', timeout=8000)
                except Exception:
                    print('DIAGNOSTYKA notice:', page.locator('#notice').inner_text(), 'errors:', errors, 'calls:', calls[-8:], flush=True)
                    raise
                assert '3,49 zł' in page.locator('#notice').inner_text()
                pickup_pin = re.search(r'PIN TESTOWY: (\d{6})', page.locator('#notice').inner_text()).group(1)
                page.wait_for_function('document.querySelector("#orders").textContent.includes("3,49 zł")')
                print('B/38 browser -> FastAPI: pickup order and 349 groszy OK')

                # B/39: delivery order and 501 groszy shipping fee.
                page.wait_for_function('[...document.querySelectorAll("#products select")].some(x => x.getAttribute("aria-label") === "Sposób realizacji zamówienia")')
                page.locator('#products select[aria-label="Sposób realizacji zamówienia"]').first.select_option('dostawa')
                page.locator('#products input[aria-label="Miejscowość dostawy"]').first.fill('Radom')
                page.locator('#products input[aria-label="Ulica i numer dostawy"]').first.fill('Leśna 4')
                page.locator('#products input[aria-label="Kod pocztowy dostawy"]').first.fill('26-600')
                page.locator('#products button', has_text='Zamów testowo').first.click()
                page.wait_for_function('document.querySelector("#notice").textContent.includes("8,50 zł")')
                assert any(m == 'POST' and path == '/orders' and status == 201 for m, path, status in calls)
                print('B/39 browser -> FastAPI: delivery order and 850 groszy OK')

                # B/41: cancel delivery through the real UI; verify stock restored once.
                delivery_order = next(o for o in client.get('/orders/me', headers={
                    'Authorization': 'Bearer ' + page.evaluate('token')
                }).json() if o['fulfillment'] == 'dostawa')
                page.wait_for_function('document.querySelectorAll("#orders button").length >= 2')
                delivery_card = page.locator('#orders .card').filter(has_text=delivery_order['pickup_code'])
                delivery_card.get_by_role('button', name='Anuluj testowo').click()
                page.wait_for_function('document.querySelector("#orders").textContent.includes("anulowane_testowo")')
                assert any(method == 'POST' and path == f"/orders/{delivery_order['id']}/cancel-test" and status == 200
                           for method, path, status in calls)
                print('B/41 delivery cancellation via UI OK')

                # B/42: repeat cancellation cannot restore inventory twice.
                client_token = page.evaluate('token')
                client_headers = {'Authorization': 'Bearer ' + client_token}
                repeat = client.post(f"/orders/{delivery_order['id']}/cancel-test", headers=client_headers)
                assert repeat.status_code == 409, repeat.text
                stock_after_cancel = client.get('/products').json()[0]['stock']
                assert stock_after_cancel == 2, stock_after_cancel
                print('B/42 repeat cancellation rejected; stock unchanged OK')

                # B/43: invalid order input rejected by backend without stock mutation.
                product_id = client.get('/products').json()[0]['id']
                invalid = client.post('/orders', headers=client_headers, json={
                    'product_id': product_id, 'quantity': 9999, 'fulfillment': 'odbior',
                    'pickup_point_id': 1
                })
                assert invalid.status_code in (409, 422), invalid.text
                assert client.get('/products').json()[0]['stock'] == stock_after_cancel
                print('B/43 insufficient stock rejected without mutation OK')

                # B/44: farmer marks pickup ready and checks wrong PIN, then correct PIN.
                logout()
                login('rolnik')
                pickup_order = next(o for o in client.get('/orders/me', headers={
                    'Authorization': 'Bearer ' + page.evaluate('token')
                }).json() if o['fulfillment'] == 'odbior')
                page.wait_for_function('document.querySelector("#orders").textContent.includes("oczekuje_na_platnosc_testowa")')
                pickup_card = page.locator('#orders .card').filter(has_text=pickup_order['pickup_code'])
                pickup_card.get_by_role('button', name='Gotowe do odbioru (test)').click()
                page.wait_for_function('document.querySelector("#orders").textContent.includes("gotowe_do_odbioru_testowo")')
                pickup_card = page.locator('#orders .card').filter(has_text=pickup_order['pickup_code'])
                pickup_card.get_by_role('textbox', name='Sześciocyfrowy PIN odbioru').fill('999999' if pickup_pin != '999999' else '888888')
                pickup_card.get_by_role('checkbox').check()
                pickup_card.get_by_role('button', name='Potwierdź odbiór').click()
                page.wait_for_function('document.querySelector("#notice").textContent.includes("pozostało prób: 4")')
                print('B/44 incorrect PIN rejected and attempt counted OK')

                # B/45: correct PIN confirms exactly once; reuse must fail.
                pickup_card = page.locator('#orders .card').filter(has_text=pickup_order['pickup_code'])
                pickup_card.get_by_role('textbox', name='Sześciocyfrowy PIN odbioru').fill(pickup_pin, timeout=5000)
                pickup_card.get_by_role('checkbox').check()
                pickup_card.get_by_role('button', name='Potwierdź odbiór').click()
                page.wait_for_function('document.querySelector("#orders").textContent.includes("odebrane")', timeout=10000)
                farmer_headers = {'Authorization': 'Bearer ' + page.evaluate('token')}
                reused = client.post(f"/orders/{pickup_order['id']}/confirm", headers=farmer_headers,
                                     json={'pin': pickup_pin, 'checked_goods': True})
                assert reused.status_code == 409, reused.text
                assert not errors, errors
                print('B/45 pickup confirmed; PIN reuse blocked OK')

                # B/46–50: delivery assignment, address access, PIN and simulated refund.
                # All data and money events are disposable; no production payment is executed.
                os.environ['WP_ENABLE_TEST_PAYMENTS'] = '1'
                courier_register = client.post('/auth/register', json={
                    'email': 'bridge-dostawca@example.invalid', 'password': password, 'role': 'dostawca'})
                assert courier_register.status_code == 201, courier_register.text
                courier_id = courier_register.json()['id']
                other_register = client.post('/auth/register', json={
                    'email': 'bridge-obcy@example.invalid', 'password': password, 'role': 'dostawca'})
                assert other_register.status_code == 201, other_register.text

                def bearer(email):
                    result = client.post('/auth/login', json={'email': email, 'password': password})
                    assert result.status_code == 200, result.text
                    return {'Authorization': 'Bearer ' + result.json()['access_token']}

                buyer_h = bearer('bridge-klient@example.invalid')
                farmer_h = bearer('bridge-rolnik@example.invalid')
                courier_h = bearer('bridge-dostawca@example.invalid')
                stranger_h = bearer('bridge-obcy@example.invalid')
                product_id = client.get('/products').json()[0]['id']
                new_order = client.post('/orders', headers=buyer_h, json={
                    'product_id': product_id, 'quantity': 1, 'fulfillment': 'dostawa',
                    'delivery_city': 'Radom', 'delivery_street': 'Tajna 9',
                    'delivery_postal_code': '26-600'})
                assert new_order.status_code == 201, new_order.text
                delivery_id = new_order.json()['id']
                delivery_pin = new_order.json()['pin_test_only']
                assert new_order.json()['total_grosze'] == 850
                location_url = f'/orders/{delivery_id}/location'
                assert client.get(location_url, headers=courier_h).status_code == 403
                assert client.get('/couriers/me/active-addresses', headers=courier_h).json() == []
                print('B/46 unassigned courier has no address OK')

                assignment_url = f'/orders/{delivery_id}/assign-courier-test'
                assert client.post(assignment_url, headers=buyer_h, json={'courier_id': courier_id}).status_code == 403
                assigned = client.post(assignment_url, headers=farmer_h, json={'courier_id': courier_id})
                assert assigned.status_code == 200, assigned.text
                assert client.post(assignment_url, headers=farmer_h, json={'courier_id': courier_id}).status_code == 409
                assert client.get(location_url, headers=courier_h).status_code == 403
                assert client.get(location_url, headers=stranger_h).status_code == 403
                print('B/47 farmer assigns exactly one courier; address remains hidden OK')

                dispatched = client.post(f'/orders/{delivery_id}/dispatch-test', headers=farmer_h)
                assert dispatched.status_code == 200, dispatched.text
                address = client.get(location_url, headers=courier_h)
                assert address.status_code == 200, address.text
                assert address.json()['delivery_street'] == 'Tajna 9'
                active = client.get('/couriers/me/active-addresses', headers=courier_h)
                assert active.status_code == 200 and len(active.json()) == 1
                assert active.json()[0]['order_id'] == delivery_id
                assert client.get(location_url, headers=stranger_h).status_code == 403
                assert client.get(location_url, headers=farmer_h).status_code == 403
                print('B/48 only active assigned courier sees delivery address OK')

                wrong_pin = '999999' if delivery_pin != '999999' else '888888'
                invalid_pin = client.post(f'/orders/{delivery_id}/confirm', headers=courier_h,
                                          json={'pin': wrong_pin, 'checked_goods': True})
                assert invalid_pin.status_code == 200 and invalid_pin.json()['remaining_attempts'] == 4
                completed = client.post(f'/orders/{delivery_id}/confirm', headers=courier_h,
                                        json={'pin': delivery_pin, 'checked_goods': True})
                assert completed.status_code == 200 and completed.json()['confirmed'] is True, completed.text
                assert client.get(location_url, headers=courier_h).status_code == 403
                assert client.get('/couriers/me/active-addresses', headers=courier_h).json() == []
                print('B/49 courier confirms with PIN; address access revoked OK')

                # Independent delivery: a courier failure after a simulated payment
                # refunds the entire 850 groszy, including 501 groszy delivery.
                failed_order = client.post('/orders', headers=buyer_h, json={
                    'product_id': product_id, 'quantity': 1, 'fulfillment': 'dostawa',
                    'delivery_city': 'Radom', 'delivery_street': 'Tajna 11',
                    'delivery_postal_code': '26-600'})
                assert failed_order.status_code == 201, failed_order.text
                failed_id = failed_order.json()['id']
                assert failed_order.json()['total_grosze'] == 850
                paid = client.post(f'/test/payments/{failed_id}/events', headers=buyer_h,
                                   json={'event_id': 'pay-b50', 'event_type': 'payment_success_test'})
                assert paid.status_code == 200, paid.text
                # Refund is allowed only after the courier has actually been dispatched.
                assign = client.post(f'/orders/{failed_id}/assign-courier-test', headers=farmer_h,
                                     json={'courier_id': courier_id})
                assert assign.status_code == 200, assign.text
                dispatch = client.post(f'/orders/{failed_id}/dispatch-test', headers=farmer_h)
                assert dispatch.status_code == 200, dispatch.text
                refund = client.post(f'/test/payments/{failed_id}/events', headers=farmer_h,
                                     json={'event_id': 'refund-b50', 'event_type': 'delivery_failed_by_courier_test'})
                assert refund.status_code == 200, refund.text
                assert refund.json()['refund_grosze'] == 850, refund.json()
                assert refund.json()['state'] == 'refunded_test', refund.json()
                repeated = client.post(f'/test/payments/{failed_id}/events', headers=farmer_h,
                                       json={'event_id': 'refund-b50', 'event_type': 'delivery_failed_by_courier_test'})
                assert repeated.status_code == 200 and repeated.json()['refund_grosze'] == 850
                print('B/50 simulated courier failure: 100% refund including delivery, idempotent OK')

                # B/40: client logout revokes browser access to private views.
                logout()
                assert page.locator('#notifications-section').is_hidden()
                assert page.locator('#dashboard-content').inner_text() == ''
                assert page.locator('#orders').inner_text() == ''
                assert not page.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
                assert not errors, errors
                print(f'B/40 session privacy and layout OK; {len(calls)} real in-process API requests')
                page.close()
            finally:
                browser.close()


if __name__ == '__main__':
    run()
