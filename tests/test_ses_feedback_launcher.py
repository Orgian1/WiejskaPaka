import json
import pytest
from scripts import serve_ses_feedback as launcher


def test_default_does_no_private_or_server_work(monkeypatch,capsys):
    def forbidden(*a,**k):pytest.fail('Disabled launcher must not prepare anything')
    monkeypatch.setattr(launcher,'prepare',forbidden)
    assert launcher.main([])==0
    assert json.loads(capsys.readouterr().out)=={'status':'DISABLED'}


@pytest.mark.parametrize('options',[{'host':'0.0.0.0'},{'host':'example.invalid'},{'port':0},{'port':65536},{'port':True}])
def test_invalid_bind_is_rejected_before_private_work(monkeypatch,options):
    def forbidden(*a,**k):pytest.fail('Unsafe bind must not access configuration')
    monkeypatch.setattr(launcher,'prepare',forbidden)
    assert launcher.execute({},serve=True,**options)=={'status':'LAUNCHER_REJECTED'}


@pytest.mark.parametrize('problem',['disabled','configuration','history'])
def test_failed_preflight_cannot_open_listener(monkeypatch,problem):
    import uvicorn
    def forbidden(*a,**k):pytest.fail('Failed preflight must not bind')
    monkeypatch.setattr(uvicorn,'run',forbidden)
    class Prepared:
        def build_app(self):raise RuntimeError('private-history-key')
    def prepare(*args):
        if problem=='configuration':raise RuntimeError('private-credentials')
        return None if problem=='disabled' else Prepared()
    monkeypatch.setattr(launcher,'prepare',prepare)
    assert launcher.execute({},serve=True)=={'status':'LAUNCHER_REJECTED'}


def test_complete_preflight_precedes_single_local_server_without_proxy_trust(monkeypatch):
    import uvicorn
    events=[];app=object()
    class Prepared:
        def build_app(self):events.append('preflight');return app
    monkeypatch.setattr(launcher,'prepare',lambda env:Prepared())
    def run(received,**kwargs):
        assert events==['preflight'] and received is app
        assert kwargs['host']=='127.0.0.1' and kwargs['port']==8011
        assert kwargs['workers']==1 and kwargs['reload'] is False
        assert kwargs['proxy_headers'] is False and kwargs['access_log'] is False
        assert kwargs['limit_concurrency']==32 and kwargs['timeout_graceful_shutdown']==5
        events.append('serve')
    monkeypatch.setattr(uvicorn,'run',run)
    assert launcher.execute({},serve=True)=={'status':'STOPPED'}
    assert events==['preflight','serve']


def test_bind_failure_is_redacted(monkeypatch):
    import uvicorn
    class Prepared:
        def build_app(self):return object()
    monkeypatch.setattr(launcher,'prepare',lambda env:Prepared())
    def broken(*a,**k):raise SystemExit('private-error')
    monkeypatch.setattr(uvicorn,'run',broken)
    assert launcher.execute({},serve=True)=={'status':'LAUNCHER_REJECTED'}
