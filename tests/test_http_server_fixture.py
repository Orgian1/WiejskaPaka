"""Bounded readiness and child cleanup without real delays or subprocesses."""
from types import SimpleNamespace
import pytest
import httpx
from tests import test_purchase_record_http_restart as fixture


@pytest.mark.parametrize('case',['slow_start','deadline','exited','consumer_error'])
def test_disposable_http_readiness_and_cleanup(monkeypatch,tmp_path,case):
    state={'seconds':0,'requests':0,'terminated':False,'waited':False}
    def sleep(seconds):state['seconds']+=seconds
    process=SimpleNamespace(
        poll=lambda:1 if case=='exited' else None,
        terminate=lambda:state.update(terminated=True),
        wait=lambda **kwargs:state.update(waited=True))
    class Socket:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def bind(self,address):assert address==('127.0.0.1',0)
        def getsockname(self):return ('127.0.0.1',54321)
    class Client:
        def __init__(self,**kwargs):
            assert kwargs['trust_env'] is False
            assert kwargs['base_url']=='http://127.0.0.1:54321'
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def get(self,path,**kwargs):
            assert path=='/health' and kwargs['timeout']==.5
            state['requests']+=1
            if case=='deadline' or (case=='slow_start' and state['requests']<=120):
                raise httpx.ConnectError('Disposable fixture not ready')
            return SimpleNamespace(status_code=200)
    monkeypatch.setattr(fixture,'time',SimpleNamespace(monotonic=lambda:state['seconds'],sleep=sleep))
    monkeypatch.setattr(fixture,'socket',SimpleNamespace(socket=Socket))
    monkeypatch.setattr(fixture,'httpx',SimpleNamespace(Client=Client,TransportError=httpx.TransportError))
    monkeypatch.setattr(fixture.subprocess,'Popen',lambda *args,**kwargs:process)
    if case in ('deadline','exited'):
        with pytest.raises(AssertionError,match='startup timeout' if case=='deadline' else 'server exited'):
            with fixture.server(tmp_path/'fixture.sqlite'):pytest.fail('Invalid server became ready')
    elif case=='consumer_error':
        with pytest.raises(ValueError,match='consumer failed'):
            with fixture.server(tmp_path/'fixture.sqlite'):raise ValueError('consumer failed')
    else:
        with fixture.server(tmp_path/'fixture.sqlite'):
            assert state['requests']==121 and 5<state['seconds']<20
    assert state['terminated'] and state['waited']
    if case=='deadline':assert 20<=state['seconds']<20.1
    if case=='exited':assert state['requests']==0 and state['seconds']==0
