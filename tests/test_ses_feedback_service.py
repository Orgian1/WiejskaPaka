import json
import sqlite3
import pytest
from fastapi.testclient import TestClient
from backend import ses_feedback_service as service,ses_feedback_archive as archive
from backend import ses_feedback as feedback,mail_suppression as blocks,ses_feedback_config
from backend.reset_mail_queue import transaction
from scripts import check_ses_feedback_service as cli
from tests.test_sns_pinned_notification import signer,NOW
from tests.test_ses_feedback import event,signed,SOURCE


def environment():
    return {'WP_ENV':'test','WP_ENABLE_SES_FEEDBACK_SERVICE':'1','WP_ENABLE_SES_FEEDBACK_CONFIG':'1',
            'WP_ENABLE_SES_REVIEW_KEYS':'1','WP_ENABLE_SES_FEEDBACK_DATABASE':'1'}


@pytest.fixture
def prepared(tmp_path,signer,monkeypatch):
    path=tmp_path/'archive.sqlite3';calls=[]
    def connect():
        con=sqlite3.connect(path);con.row_factory=sqlite3.Row;calls.append(con)
        return con
    con=connect()
    try:con.executescript(archive.SCHEMA_SQLITE+feedback.SCHEMA_SQLITE+blocks.SCHEMA_SQLITE)
    finally:con.close()
    calls.clear()
    config=ses_feedback_config.FeedbackConfig(signer[1].topic_arn,SOURCE,(signer[1],))
    cipher=archive.ArchiveCipher({'old':b'o'*32},'old')
    monkeypatch.setattr(service.ses_feedback_config,'load_config',lambda *a,**k:config)
    monkeypatch.setattr(service.ses_review_keys,'load_config',lambda *a,**k:cipher)
    monkeypatch.setattr(service.ses_feedback_database,'load_config',lambda *a,**k:connect)
    return service.prepare(environment(),now=NOW),calls


def test_prepare_does_not_connect_and_check_closes_probe(prepared):
    item,calls=prepared
    assert not calls and 'certificate' not in repr(item) and 'oooo' not in repr(item)
    assert item.check(now=NOW)=={'status':'CONFIGURATION_VALID','retained_records':0}
    with pytest.raises(sqlite3.ProgrammingError):calls[0].execute('SELECT 1')


def test_combined_build_validates_then_http_commits(prepared,signer):
    item,calls=prepared
    app=item.build_app(clock=lambda:NOW)
    assert len(calls)==1
    with TestClient(app) as client:
        assert client.post('/sns/feedback',content=signed(signer,event(bounce_type='Undetermined'))).status_code==204
    assert item.check(now=NOW)['retained_records']==1


def test_wrong_historical_material_prevents_app_construction(prepared,signer):
    item,_=prepared;con=item.target()
    try:
        with transaction(con):archive.receive(con,signed(signer,event(bounce_type='Undetermined')),item.config,item.cipher,now=NOW)
    finally:con.close()
    wrong=service.Prepared(item.config,archive.ArchiveCipher({'old':b'w'*32},'old'),item.target)
    with pytest.raises(ValueError,match='^SES_FEEDBACK_SERVICE_REJECTED$'):wrong.build_app(clock=lambda:NOW)


def test_disabled_and_partial_opt_ins_read_nothing(monkeypatch):
    def forbidden(*a,**k):pytest.fail('No private reads without complete opt-in')
    monkeypatch.setattr(service.ses_feedback_config,'load_config',forbidden)
    assert service.prepare({}) is None
    assert cli.check(environment())=={'status':'DISABLED'}
    for flag in ('WP_ENABLE_SES_FEEDBACK_CONFIG','WP_ENABLE_SES_REVIEW_KEYS','WP_ENABLE_SES_FEEDBACK_DATABASE'):
        env=environment();env.pop(flag)
        with pytest.raises(ValueError,match='^SES_FEEDBACK_SERVICE_REJECTED$'):service.prepare(env)


@pytest.mark.parametrize('name,value',[
    ('WP_SES_REVIEW_MAX_RECORDS','0'),('WP_SES_REVIEW_MAX_RECORDS','10001'),
    ('WP_SES_REVIEW_RETENTION_SECONDS','3599'),('WP_SES_REVIEW_RETENTION_SECONDS','2592001'),
    ('WP_SES_FEEDBACK_BODY_TIMEOUT','31'),('WP_SES_FEEDBACK_MAX_INFLIGHT','33'),
    ('WP_SES_REVIEW_MAX_RECORDS','01'),('WP_SES_REVIEW_MAX_RECORDS',True)])
def test_invalid_policies_fail_before_private_reads(monkeypatch,name,value):
    def forbidden(*a,**k):pytest.fail('Invalid policy must not read private files')
    monkeypatch.setattr(service.ses_feedback_config,'load_config',forbidden)
    env=environment();env[name]=value
    with pytest.raises(ValueError,match='^SES_FEEDBACK_SERVICE_REJECTED$'):service.prepare(env)


def test_valid_policy_snapshot_and_redacted_cli(prepared,monkeypatch,capsys):
    _,calls=prepared;env=environment()
    env.update(WP_SES_REVIEW_MAX_RECORDS='9',WP_SES_REVIEW_RETENTION_SECONDS='3600',
               WP_SES_FEEDBACK_BODY_TIMEOUT='2',WP_SES_FEEDBACK_MAX_INFLIGHT='1')
    item=service.prepare(env,now=NOW)
    assert (item.max_records,item.retention_seconds,item.body_timeout,item.max_inflight)==(9,3600,2,1)
    assert not calls
    monkeypatch.setattr(cli,'prepare',lambda *a,**k: (_ for _ in ()).throw(RuntimeError('private-secret')))
    assert cli.main(['--check'])==1
    assert json.loads(capsys.readouterr().out)=={'status':'CONFIGURATION_REJECTED'}



def test_expired_snapshot_cannot_start_or_connect(prepared):
    item,calls=prepared
    with pytest.raises(ValueError,match='^SES_FEEDBACK_SERVICE_REJECTED$'):item.check(now=NOW+9*86400)
    assert not calls


def test_probe_error_is_redacted_and_connection_closed(prepared,monkeypatch):
    item,calls=prepared
    def broken(*a,**k):raise RuntimeError('private-address-key')
    monkeypatch.setattr(service,'check_retained',broken)
    with pytest.raises(ValueError,match='^SES_FEEDBACK_SERVICE_REJECTED$'):item.check(now=NOW)
    with pytest.raises(sqlite3.ProgrammingError):calls[-1].execute('SELECT 1')
