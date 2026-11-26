"""Manual CRM workflow over real HTTP, using disposable SQLite and PostgreSQL."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
import sqlite3
from contextlib import closing
from uuid import uuid4

import pytest

from backend.incubator_invoicing import MIGRATION, create_sqlite_schema, summary, today
from tests.browser_login_guide import dismiss_login_guide
from tests.test_admin_seller_review import create_admin
from tests.test_postgres_full_api_optin import _postgres_api, inspection_connect, rls_requested
from tests.test_purchase_record_http_restart import server
from tests.test_sample_demo_browser import sample_browser_server
from tests.test_wallet_withdrawal_lifecycle import setup, complete, cancel


BASE = '/admin/incubator-invoicing'


@pytest.fixture(params=['sqlite', 'postgres'])
def api(request, tmp_path, monkeypatch):
    if request.param == 'postgres':
        for native in _postgres_api(wallet=True, incubator=True):
            client, parameters = native

            def promote(uid):
                with inspection_connect(**parameters) as con:
                    con.execute("UPDATE users SET role='admin' WHERE id=%s", (uid,))

            yield client, create_admin(client, promote)[0], native.restart
        return
    monkeypatch.setenv('WP_ENABLE_WALLET_PREVIEW', '1')
    database = tmp_path / 'incubator.sqlite3'
    with server(database) as client:
        def promote(uid):
            with sqlite3.connect(database) as con:
                con.execute("UPDATE users SET role='admin' WHERE id=?", (uid,))

        yield client, create_admin(client, promote)[0], None


def reference(**kwargs):
    stamp = today().isoformat()
    return dict(transaction_id=uuid4().hex, operator_settlement_id='PSP-BATCH-32',
                transaction_on=stamp, settled_on=stamp, amount_grosze=1000, confirmed=True) | kwargs


def credit(**kwargs):
    return reference(kind='pickup_point', buyer_name='=Example buyer', buyer_address='Łąkowa 12',
                     buyer_nip='1234567890') | kwargs


def issue(amount, number='FS/1'):
    return dict(invoice_number=number, issued_on=today().isoformat(), expected_grosze=amount)


def listing(client, admin, **params):
    response = client.get(BASE, headers=admin, params=params)
    assert response.status_code == 200, response.text
    assert response.headers['Cache-Control'] == 'no-store'
    return response.json()


def test_permissions_withdrawal_source_and_monthly_grouping(api):
    client, admin, _ = api
    assert client.get(BASE).status_code == 401
    seller, withdrawal_id = setup(client)
    customer, customer_id = setup(client, 'klient')
    for user in (seller, customer):
        assert client.get(BASE, headers=user).status_code == 403
        assert client.get(BASE + '/export.csv', headers=user).status_code == 403
        assert client.post(BASE, headers=user, json=credit()).status_code == 403
    assert listing(client, admin)['items'] == []
    entry = credit(kind='withdrawal_fee', transaction_id=withdrawal_id, amount_grosze=200)
    assert client.post(BASE, headers=admin, json=entry).status_code == 409  # reserved
    assert complete(client, admin, customer_id).status_code == 201
    assert client.post(BASE, headers=admin, json=dict(entry, transaction_id=customer_id)).status_code == 409
    assert complete(client, admin, withdrawal_id).status_code == 201
    assert client.post(BASE, headers=admin, json=dict(entry, amount_grosze=4001)).status_code == 422
    created = client.post(BASE, headers=admin, json=entry)
    assert created.status_code == 201, created.text
    assert client.post(BASE, headers=admin, json=dict(entry, operator_settlement_id='retry')).status_code == 409
    snapshot = listing(client, admin, status='pending')
    assert snapshot['items'][0]['invoice_grosze'] == 200
    assert snapshot['items'][0]['withdrawal_gross_grosze'] == 4001
    assert snapshot['summary']['commission_grosze'] == '200'
    assert snapshot['summary']['revenue_grosze'] == '200'
    group = client.get(BASE+'/seller-summary', headers=admin, params={'month': today().strftime('%Y-%m')})
    assert group.status_code == 200, group.text
    assert [(i['kind'], i['amount_grosze']) for i in group.json()['items']] == [('seller_withdrawal_fee', 200)]
    assert client.post(BASE, headers=admin, json=credit(kind='wallet_topup')).status_code == 422
    assert client.post(BASE, headers=admin, json=credit(mode='verified')).status_code == 409
    assert client.post(BASE, headers=admin, json=credit(amount_grosze=1000.0)).status_code == 422
    assert client.post(BASE, headers=admin, json=credit(confirmed=False)).status_code == 422
    owner, cancelled = setup(client)
    assert cancel(client, owner, cancelled).status_code == 201
    assert client.post(BASE, headers=admin, json=dict(entry, transaction_id=cancelled)).status_code == 409


def test_reconciled_refunds_immutable_invoice_and_duplicate_number(api):
    client, admin, restart = api
    created = client.post(BASE, headers=admin, json=credit())
    assert created.status_code == 201, created.text
    entry = created.json()['id']
    refund_url = f'{BASE}/{entry}/refund'
    issue_url = f'{BASE}/{entry}/issue'
    pre = reference(amount_grosze=250)
    assert client.post(refund_url, headers=admin, json=pre).status_code == 201
    assert client.post(refund_url, headers=admin, json=pre).status_code == 409
    assert client.post(issue_url, headers=admin, json=issue(1000)).status_code == 409
    marked = client.post(issue_url, headers=admin, json=issue(750))
    assert marked.status_code == 200, marked.text
    assert client.post(issue_url, headers=admin, json=issue(750, 'FS/2')).status_code == 409
    assert client.post(refund_url, headers=admin, json=reference(amount_grosze=751)).status_code == 409
    post = client.post(refund_url, headers=admin, json=reference(amount_grosze=100))
    assert post.status_code == 201, post.text
    fix_url = f'{BASE}/{post.json()["id"]}/issue'
    assert client.post(fix_url, headers=admin, json=issue(-100, 'fs/1')).status_code == 409
    assert client.post(fix_url, headers=admin, json=issue(-100, 'K/1')).status_code == 200
    if restart:
        restart()
    issued = listing(client, admin, status='issued', month=today().strftime('%Y-%m'))
    assert {i['invoice_number']: i['invoice_grosze'] for i in issued['items']} == {'FS/1': 750, 'K/1': -100}
    assert next(i for i in issued['items'] if i['kind']=='refund')['original_invoice_number']=='FS/1'
    assert issued['summary'] == {'issued': 2, 'free_remaining': 98, 'extra_cost_grosze': 0,
                                 'revenue_grosze': '650', 'commission_grosze': '0'}
    assert len(listing(client, admin, status='closed')['items']) == 1
    assert len(listing(client, admin, search='=Example', kind='pickup_point')['items']) == 1
    assert listing(client, admin, search='%')['items'] == []
    csv = client.get(BASE+'/export.csv', headers=admin, params={'status':'issued'})
    assert csv.status_code == 200 and "'=Example buyer" in csv.text
    assert 'Łąkowa 12' in csv.text and 'FS/1' in csv.text


def test_concurrent_issue_and_total_cancellation(api):
    client, admin, _ = api
    transaction = credit(kind='advertising')
    with ThreadPoolExecutor(2) as pool:
        created = list(pool.map(lambda _: client.post(BASE, headers=admin, json=transaction), range(2)))
    assert sorted(r.status_code for r in created) == [201, 409]
    item = next(r.json()['id'] for r in created if r.status_code == 201)
    with ThreadPoolExecutor(2) as pool:
        codes = list(pool.map(lambda n: client.post(f'{BASE}/{item}/issue', headers=admin,
                                                   json=issue(1000, f'FS/{n}')).status_code, range(2)))
    assert sorted(codes) == [200, 409]
    item = client.post(BASE, headers=admin, json=credit()).json()['id']
    with ThreadPoolExecutor(2) as pool:
        codes = list(pool.map(lambda _: client.post(f'{BASE}/{item}/refund', headers=admin,
                                  json=reference()).status_code, range(2)))
    assert sorted(codes) == [201, 409]
    assert client.post(f'{BASE}/{item}/issue', headers=admin, json=issue(1000)).status_code == 409


def test_verified_admin_reconciliation_on_postgres_rls_only():
    if not rls_requested():
        pytest.skip('Run this test with the PostgreSQL RLS gate')
    import psycopg
    for native in _postgres_api(wallet=True, incubator=True, incubator_verified=True):
        client, parameters = native

        def promote(uid):
            with inspection_connect(**parameters) as con:
                con.execute("UPDATE users SET role='admin' WHERE id=%s", (uid,))

        admin = create_admin(client, promote)[0]
        seller, _ = setup(client)
        seller_id = client.get('/auth/me', headers=seller).json()['id']
        with inspection_connect(**parameters) as con:
            con.execute(MIGRATION.read_text())
        with psycopg.connect(**parameters) as runtime:
            grants = runtime.execute("""
                SELECT has_table_privilege(current_user,'incubator_invoice_entries','SELECT'),
                       has_table_privilege(current_user,'incubator_invoice_entries','INSERT')""").fetchone()
            assert grants == (False, False)
        snapshot = client.get(BASE+'/config', headers=admin)
        assert snapshot.json()['verified_enabled'] is True
        entry = credit(mode='verified', kind='withdrawal_fee', seller_id=seller_id,
                       amount_grosze=201, withdrawal_gross_grosze=4010)
        assert client.post(BASE, headers=admin, json=dict(entry, amount_grosze=200)).status_code == 422
        created = client.post(BASE, headers=admin, json=entry)
        assert created.status_code == 201, created.text
        verified = listing(client, admin, mode='verified')
        assert verified['items'][0]['invoice_grosze'] == 201
        assert listing(client, admin, mode='test')['items'] == []
        assert client.get(BASE, headers=seller, params={'mode':'verified'}).status_code == 403
        assert client.post(f"{BASE}/{created.json()['id']}/issue", headers=admin,
                           json=issue(201, 'CRM/1')).status_code == 200


@pytest.mark.parametrize(('count', 'cost'), [(99,0), (100,0), (101,4000), (200,4000), (201,8000)])
def test_invoice_quota_has_integer_block_cost_and_separate_calendar(count, cost):
    with closing(sqlite3.connect(':memory:')) as con:
        con.row_factory = sqlite3.Row
        create_sqlite_schema(con)
        con.executemany("""INSERT INTO incubator_invoice_entries
            (id,mode,kind,buyer_name,buyer_address,service,transaction_id,operator_settlement_id,
             transaction_on,settled_on,amount_grosze,recorded_by,created_at,
             invoice_number,invoice_number_key,invoice_amount_grosze,issued_on,issued_by)
             VALUES (?,'test','advertising','Test','Test','Reklama',?,'batch','2026-10-30','2026-10-31',
                     100,1,'2026-11-01',?,?,100,'2026-11-01',1)""",
            [(str(i),str(i),str(i),str(i)) for i in range(count)])
        nov = summary(con,'test','2026-11')
        assert (nov['issued'],nov['free_remaining'],nov['extra_cost_grosze']) == (count,max(0,100-count),cost)
        assert nov['revenue_grosze'] == '0'
        assert summary(con,'test','2026-10')['revenue_grosze'] == str(count*100)
        assert summary(con,'verified','2026-11')['issued'] == 0


def test_admin_crm_tab_in_chromium(sample_browser_server):
    browser, url, accounts = sample_browser_server
    page = browser.new_page(viewport={'width': 390, 'height': 850}, accept_downloads=True)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    try:
        page.goto(url)
        page.click('#account-nav-link')
        page.fill('#email', accounts['admin']['email'])
        page.fill('#password', accounts['admin']['password'])
        page.locator('#auth button[type=submit]').click()
        dismiss_login_guide(page)
        page.click('#panel-nav-link')
        tab = page.get_by_test_id('incubator-invoicing')
        tab.locator(':scope > summary').click()
        tab.get_by_text('Brak pozycji dla wybranego filtra.').wait_for()
        tab.get_by_text('Zapisz wpływ dla platformy').click()
        form = tab.locator('form').first
        form.get_by_label('Rodzaj usługi').select_option('advertising')
        form.get_by_label('Nabywca', exact=True).fill('Fikcyjny nabywca')
        form.get_by_label('Adres nabywcy').fill('Fikcyjna 1, 00-000 Testowo')
        form.get_by_label('Numer transakcji').fill(uuid4().hex)
        form.get_by_label('Identyfikator rozliczenia operatora').fill('Test PSP')
        form.get_by_label('Data transakcji').fill(today().isoformat())
        form.get_by_label('Kwota dla platformy (w groszach)').fill('1299')
        form.get_by_label('Potwierdzam dane rozliczenia').check()
        form.get_by_role('button', name='Zapisz wpływ').click()
        tab.get_by_text('Kwota do faktury: 12,99 zł').wait_for()
        page.context.grant_permissions(['clipboard-read', 'clipboard-write'])
        tab.get_by_role('button', name='Kopiuj dane do CRM').click()
        assert 'Fikcyjny nabywca' in page.evaluate('navigator.clipboard.readText()')
        tab.get_by_label('Numer wystawionej faktury').fill('TEST-CRM-1')
        tab.get_by_role('button', name='Oznacz jako wystawioną').click()
        tab.get_by_text('Brak pozycji dla wybranego filtra.').wait_for()
        tab.get_by_label('Status', exact=True).select_option('issued')
        tab.get_by_role('button', name='Szukaj', exact=True).click()
        tab.get_by_text('Wystawiono: TEST-CRM-1', exact=False).wait_for()
        with page.expect_download() as download:
            tab.get_by_role('button', name='Eksportuj CSV').click()
        assert 'TEST-CRM-1' in Path(download.value.path()).read_text(encoding='utf-8-sig')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.click('#logout')
        assert tab.count() == 0
        assert not errors
    finally:
        page.close()
