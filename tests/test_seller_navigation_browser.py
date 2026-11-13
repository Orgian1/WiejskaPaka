"""Distinct browser contexts share account order; stale changes are rejected."""
from pathlib import Path
import pytest
from tests.test_sample_demo_browser import sample_browser_server
from tests.test_sample_demo import prepare_sample
from tests.test_purchase_record_http_restart import server
from tests.test_owner_finalization import login
from tests.test_next_package_browser import sign_in


@pytest.mark.parametrize('width',[320,1280])
def test_route_order_across_devices_and_stale_device(sample_browser_server,tmp_path,width):
    browser,_,_=sample_browser_server
    sample=prepare_sample(tmp_path/'route-devices');accounts=sample['credentials']
    with server(Path(sample['database'])) as client:
        farmer=login(client,accounts['rolnik'])
        created=client.post('/pickup-points',headers=farmer,json={'name':'Drugi punkt','city':'Legnica','street':'Testowa 9','opening_hours':'9-16'})
        assert created.status_code==201
        contexts=[browser.new_context(viewport={'width':w,'height':900},is_mobile=w==320,has_touch=w==320) for w in (width,1280 if width==320 else 320)]
        pages=[c.new_page() for c in contexts];errors=[]
        try:
            for page in pages:
                page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto(str(client.base_url));sign_in(page,accounts,'rolnik')
                page.locator('#seller-point-nav > summary').click()
                page.get_by_role('button',name='Przesuń wyżej: Drugi punkt',exact=True).wait_for()
                page.wait_for_function('()=>!document.querySelectorAll("#seller-point-menu li button")[2].disabled')
            move=pages[0].get_by_role('button',name='Przesuń wyżej: Drugi punkt',exact=True)
            with pages[0].expect_response('**/farmers/me/navigation') as saved:
                move.tap() if width==320 else move.click()
            assert saved.value.status==200
            pages[0].wait_for_function('()=>document.querySelector("#seller-point-menu li").textContent.includes("Drugi punkt")')
            # Device 2 still has revision zero. Its change must not erase device 1.
            with pages[1].expect_response(lambda r:r.request.method=='PUT' and r.url.endswith('/farmers/me/navigation')) as stale:
                pages[1].get_by_role('button',name='Przesuń wyżej: Drugi punkt',exact=True).click()
            assert stale.value.status==409
            pages[1].wait_for_function('()=>document.querySelector("#seller-point-menu li").textContent.includes("Drugi punkt")')
            assert 'innym urządzeniu' in pages[1].locator('#notice').inner_text()
            # A brand new context has no localStorage and reads the same saved order.
            contexts[1].close();contexts[1]=browser.new_context(viewport={'width':320,'height':900},is_mobile=True,has_touch=True)
            page=contexts[1].new_page();page.goto(str(client.base_url));sign_in(page,accounts,'rolnik')
            page.locator('#seller-point-nav > summary').click()
            page.wait_for_function('()=>document.querySelector("#seller-point-menu li")?.textContent.includes("Drugi punkt")')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            assert page.evaluate('Object.keys(localStorage).every(k=>!k.startsWith("wp-point-order:"))')
            page.click('#logout');assert page.locator('#seller-point-menu li').count()==0
            assert not errors
        finally:
            for context in contexts:context.close()


@pytest.mark.parametrize('width',[320,1280])
def test_navigation_batches_keep_all_nine_points_in_saved_order(sample_browser_server,tmp_path,width):
    from urllib.parse import urlsplit,parse_qs
    browser,_,_=sample_browser_server
    sample=prepare_sample(tmp_path/'long-route');accounts=sample['credentials']
    with server(Path(sample['database'])) as client:
        farmer=login(client,accounts['rolnik'])
        for i in range(8):
            result=client.post('/pickup-points',headers=farmer,json={'name':f'Punkt {i}','city':'Legnica','street':f'Testowa {i+1}','opening_hours':'9-16'})
            assert result.status_code==201
        points=client.get('/farmers/me/pickup-points',headers=farmer).json()[::-1]
        assert len(points)==9
        state=client.get('/farmers/me/navigation',headers=farmer).json()
        assert client.put('/farmers/me/navigation',headers=farmer,json={'revision':state['revision'],'point_ids':[p['id'] for p in points]}).status_code==200
        page=browser.new_page(viewport={'width':width,'height':900},is_mobile=width==320,has_touch=width==320)
        try:
            page.goto(str(client.base_url));sign_in(page,accounts,'rolnik')
            page.locator('#seller-point-nav > summary').click()
            page.wait_for_function('()=>document.querySelectorAll("#seller-point-menu li").length===9')
            page.get_by_text('Kolejność zapisana na koncie',exact=False).wait_for()
            links=page.locator('#seller-point-menu a[href^="https://www.google.com/maps/dir/"]')
            assert links.count()==3
            addresses=[f"{p['street']}, {p['city']}, Polska" for p in points]
            visited=[]
            for i in range(links.count()):
                params=parse_qs(urlsplit(links.nth(i).get_attribute('href')).query)
                assert params['travelmode']==['driving']
                if i:assert params['origin']==[visited[-1]]
                waypoints=params.get('waypoints',[''])[0].split('|') if params.get('waypoints') else []
                assert len(waypoints)<=3
                visited+=waypoints+params['destination']
            assert visited==addresses
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        finally:page.close()
