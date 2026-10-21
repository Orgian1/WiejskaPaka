"""Public aliases never become authentication identifiers or expose email."""
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
import sqlite3
import pytest
from fastapi.testclient import TestClient
from backend import app as module
from backend import seller_directory as directory


@pytest.fixture(scope='module')
def api():
    patch=pytest.MonkeyPatch();patch.setenv('WP_ENABLE_SELLER_SEARCH','1')
    with module.db() as con:con.executescript(directory.SCHEMA_SQLITE)
    client=TestClient(module.app)
    yield client
    patch.undo()


def account(client,role='rolnik'):
    data={'email':uuid4().hex+'@example.invalid','password':'PrivateSellerLogin2026','role':role}
    result=client.post('/auth/register',json=data);assert result.status_code==201,result.text
    token=client.post('/auth/login',json=data).json()['access_token']
    return {'Authorization':'Bearer '+token},result.json()['id'],data


def claim(client,headers,login):
    return client.put('/sellers/me/login',headers=headers,json={'login':login})


def profile(client,headers,name,city='Legnica'):
    result=client.put('/farmers/me/profile',headers=headers,json={'farm_name':name,'city':city,'description':'Opis prywatnego konta nie jest zwracany w liście.'})
    assert result.status_code==200,result.text


def test_case_insensitive_unique_handles_are_separate_from_email(api):
    first,uid,credentials=account(api);second,_,_=account(api)
    login='m_'+uuid4().hex[:10]
    assert api.get('/sellers/me/login',headers=first).json()=={'login':None}
    assert claim(api,first,'@'+login.upper()).json()=={'login':login}
    assert claim(api,second,login.upper()).status_code==409
    assert api.get('/sellers/me/login',headers=second).json()=={'login':None}
    previous='old_'+uuid4().hex[:10]
    assert claim(api,second,previous).status_code==200
    assert claim(api,second,login).status_code==409
    assert api.get('/sellers/me/login',headers=second).json()=={'login':previous}
    assert claim(api,first,login).status_code==200
    assert api.post('/auth/login',json=credentials).status_code==200
    assert api.post('/auth/login',json={'email':login,'password':credentials['password']}).status_code!=200
    result=api.get('/sellers/search',params={'q':'@'+login.upper()}).json()
    assert result['total']==1
    assert result['items']==[{'farmer_id':uid,'login':login,'farm_name':'','city':''}]
    assert credentials['email'] not in str(result)
    assert api.get('/sellers/search',params={'q':credentials['email']}).json()['total']==0


@pytest.mark.parametrize('login',['admin','ADMIN','wiejskapaka','12abc','ab','a-b','zażółć','a b','a@example.com','a'*31,'a\nxx'])
def test_invalid_or_reserved_login_is_rejected(api,login):
    # Validation must also work without constructing an account or touching SQL.
    from fastapi import HTTPException
    with pytest.raises(HTTPException):directory.normalize_login(login)


def test_roles_and_extra_fields_cannot_claim_another_identity(api):
    buyer,uid,_=account(api,'klient')
    assert claim(api,buyer,'buyer_alias').status_code==403
    assert api.get('/sellers/me/login',headers=buyer).status_code==403
    assert api.put('/sellers/me/login',json={'login':'no_session'}).status_code==401
    farmer,_,_=account(api)
    assert api.put('/sellers/me/login',headers=farmer,json={'login':'own_alias','user_id':uid}).status_code==422


def test_polish_farm_name_search_and_live_profile_updates(api):
    farmer,uid,_=account(api);login='p_'+uuid4().hex[:10]
    profile(api,farmer,'Łąka Żółte Pomidory')
    assert claim(api,farmer,login).status_code==200
    data=api.get('/sellers/search',params={'q':'LAKA ZOLTE'}).json()
    row=next(s for s in data['items'] if s['farmer_id']==uid)
    assert set(row)=={'farmer_id','login','farm_name','city'}
    assert row['farm_name']=='Łąka Żółte Pomidory' and row['city']=='Legnica'
    assert api.get('/sellers/search',params={'q':'@LAKA ZOLTE'}).json()['total']==0
    profile(api,farmer,'Nowy Sad '+login)
    assert all(s['farmer_id']!=uid for s in api.get('/sellers/search',params={'q':'LAKA ZOLTE'}).json()['items'])
    assert api.get('/sellers/search',params={'q':'Nowy Sad '+login}).json()['items'][0]['farmer_id']==uid


def test_literal_wildcards_pagination_and_exact_handle_first(api):
    prefix='z'+uuid4().hex[:10];ids=[]
    for login in (prefix, prefix+'_more', 'a_'+prefix):
        farmer,uid,_=account(api);ids.append(uid)
        assert claim(api,farmer,login).status_code==200
    first=api.get('/sellers/search',params={'q':prefix,'limit':2}).json()
    second=api.get('/sellers/search',params={'q':prefix,'limit':2,'offset':2}).json()
    assert first['total']==second['total']==3
    assert first['items'][0]['login']==prefix
    assert [r['farmer_id'] for r in first['items']+second['items']]==ids
    for q in ('%', "' OR 1=1 --",'\\'):
        assert api.get('/sellers/search',params={'q':q}).json()['total']==0
    assert api.get('/sellers/search',params={'q':'_'}).json()['total']<api.get('/sellers/search').json()['total']
    for params in ({'limit':0},{'limit':101},{'offset':10001},{'q':'a'*121},{'q':'@'}):
        assert api.get('/sellers/search',params=params).status_code==422


def test_selected_seller_filters_catalog_without_changing_regular_search(api):
    farmers=[account(api),account(api)];ids=[]
    name='Produkt '+uuid4().hex
    for headers,_,_ in farmers:
        response=api.post('/products',headers=headers,json={'name':name,'stock':5,'price_grosze':200,'delivery_grosze':500})
        assert response.status_code==201;ids.append(response.json()['id'])
    assert api.get('/catalog/search',params={'q':name}).json()['total']==2
    data=api.get('/catalog/search',params={'q':name,'farmer_id':farmers[0][1]}).json()
    assert data['total']==1 and data['items'][0]['id']==ids[0]
    for value in (0,-1,10**25):
        assert api.get('/catalog/search',params={'farmer_id':value}).status_code==422


def test_competing_claims_have_exactly_one_winner(api):
    farmers=[account(api)[0],account(api)[0]];login='race_'+uuid4().hex[:10]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda headers:claim(api,headers,login).status_code,farmers))
    assert sorted(results)==[200,409]
    with module.db() as con:
        assert con.execute('SELECT COUNT(*) AS n FROM seller_public_logins WHERE login=?',(login,)).fetchone()['n']==1


def test_feature_off_then_reindex_and_session_revocation(api,monkeypatch):
    farmer,uid,_=account(api);login='s_'+uuid4().hex[:10]
    profile(api,farmer,'Dawna nazwa '+login);assert claim(api,farmer,login).status_code==200
    monkeypatch.setenv('WP_ENABLE_SELLER_SEARCH','0')
    assert api.get('/sellers/config').json()=={'enabled':False}
    assert api.get('/sellers/search').status_code==503
    assert claim(api,farmer,login).status_code==503
    profile(api,farmer,'Żółty Sad '+login)
    monkeypatch.setenv('WP_ENABLE_SELLER_SEARCH','1')
    with module.db() as con:directory.refresh_index(con)
    assert api.get('/sellers/search',params={'q':'zolty sad '+login}).json()['items'][0]['farmer_id']==uid
    original=directory.normalize_login
    def revoke(value):
        value=original(value)
        with module.db() as con:con.execute('DELETE FROM sessions WHERE user_id=?',(uid,))
        return value
    monkeypatch.setattr(directory,'normalize_login',revoke)
    assert claim(api,farmer,'replacement_'+uuid4().hex[:8]).status_code==401
    with module.db() as con:
        assert con.execute('SELECT login FROM seller_public_logins WHERE user_id=?',(uid,)).fetchone()['login']==login


def test_database_checks_forbid_case_and_invalid_char_bypass(api):
    farmer,uid,_=account(api)
    with module.db() as con:
        for invalid in ('UPPERCASE','12login','a-b','zażółć'):
            with pytest.raises(sqlite3.IntegrityError):
                con.execute('INSERT INTO seller_public_logins(user_id,login,farm_name_key) VALUES(?,?,?)',(uid,invalid,''))
