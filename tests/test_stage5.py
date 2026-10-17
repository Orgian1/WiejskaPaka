import importlib
import os
from fastapi.testclient import TestClient


def test_login_lock_and_logout_all(tmp_path):
    os.environ['WIEJSKAPAKA_DB'] = str(tmp_path / 'stage5.sqlite3')
    import backend.app as module
    module = importlib.reload(module)
    client = TestClient(module.app)
    email = 'security@example.test'
    assert client.post('/auth/register', json={'email':email,'password':'very-long-password-123','role':'klient'}).status_code == 201
    for _ in range(5):
        assert client.post('/auth/login', json={'email':email,'password':'wrong'}).status_code == 401
    assert client.post('/auth/login', json={'email':email,'password':'very-long-password-123'}).status_code == 429
    assert client.get('/health').headers['x-content-type-options'] == 'nosniff'
    with module.db() as con:
        con.execute('DELETE FROM login_attempts WHERE email=?', (email,))
    auth = client.post('/auth/login', json={'email':email,'password':'very-long-password-123'}).json()['access_token']
    headers = {'Authorization':f'Bearer {auth}'}
    assert client.post('/auth/logout-all', headers=headers).status_code == 200
    assert client.get('/auth/me', headers=headers).status_code == 401
