import json
import sqlite3
import threading
import pytest
from fastapi.testclient import TestClient
from backend import ses_feedback as feedback,mail_suppression as blocks
from backend import ses_feedback_archive as archive,ses_feedback_config as config,ses_feedback_http as http
from tests.test_sns_pinned_notification import signer,NOW
from tests.test_ses_feedback import event,signed,SOURCE


@pytest.fixture
def setup(tmp_path,signer):
    path=tmp_path/'private.sqlite3'
    def connect():
        con=sqlite3.connect(path);con.row_factory=sqlite3.Row;con.execute('PRAGMA foreign_keys=ON')
        return con
    con=connect()
    try:con.executescript(feedback.SCHEMA_SQLITE+blocks.SCHEMA_SQLITE+archive.SCHEMA_SQLITE)
    finally:con.close()
    trusted=config.FeedbackConfig(signer[1].topic_arn,SOURCE,(signer[1],))
    cipher=archive.ArchiveCipher({'archive':b'a'*32},'archive')
    return connect,trusted,cipher


def client(setup,**changes):
    connect,trusted,cipher=setup
    return TestClient(http.create_app(trusted,cipher,connect,clock=lambda:NOW,**changes))


def count(setup,table):
    con=setup[0]()
    try:return con.execute('SELECT count(*) FROM '+table).fetchone()[0]
    finally:con.close()


def test_ack_only_after_committed_review_and_idempotent_retry(setup,signer):
    raw=signed(signer,event(bounce_type='Undetermined'))
    with client(setup) as c:
        first=c.post('/sns/feedback',content=raw,headers={'content-type':'text/plain'})
        assert first.status_code==204 and first.content==b''
        assert count(setup,'ses_feedback_events')==count(setup,'ses_feedback_review')==1
        assert c.post('/sns/feedback',content=raw).status_code==204
        assert count(setup,'ses_feedback_review')==1
        for path in ('/docs','/openapi.json','/sns/feedback'):
            assert c.get(path).status_code in (404,405)
    con=setup[0]()
    try:
        row=con.execute('SELECT * FROM ses_feedback_review').fetchone()
        assert setup[2].open(row)==raw.encode()
    finally:con.close()


def test_bounce_commits_block_before_ack(setup,signer):
    with client(setup) as c:assert c.post('/sns/feedback',content=signed(signer,event())).status_code==204
    con=setup[0]()
    try:assert blocks.blocked(con,'buyer@example.invalid')
    finally:con.close()
    assert count(setup,'ses_feedback_review')==0


@pytest.mark.parametrize('problem',['signature','unapproved-pin','stale','subscription','bad-json'])
def test_untrusted_events_have_no_success_ack_or_writes(setup,signer,problem):
    raw=signed(signer,event(bounce_type='Undetermined'))
    if problem=='signature':raw=raw.replace('Undetermined','Permanent')
    elif problem=='unapproved-pin':raw=raw.replace('synthetic.pem','unknown.pem')
    elif problem=='stale':
        from tests.test_sns_pinned_notification import envelope
        raw=json.dumps(envelope(signer[0],json.dumps(event()),Timestamp='2020-01-01T00:00:00Z'))
    elif problem=='subscription':
        from tests.test_sns_pinned_notification import envelope
        raw=json.dumps(envelope(signer[0],Type='SubscriptionConfirmation'))
    elif problem=='bad-json':raw='{"private-secret":'
    with client(setup) as c:
        response=c.post('/sns/feedback',content=raw)
        assert response.status_code==503 and response.content==b''
    assert count(setup,'ses_feedback_events')==count(setup,'ses_feedback_review')==0


def test_archive_capacity_failure_does_not_ack_or_leave_journal(setup,signer):
    one=signed(signer,event(bounce_type='Undetermined'))
    two=signed(signer,event(bounce_type='Undetermined'),MessageId='22345678-1234-1234-1234-123456789abc')
    with client(setup,max_records=1) as c:
        assert c.post('/sns/feedback',content=one).status_code==204
        assert c.post('/sns/feedback',content=two).status_code==503
    assert count(setup,'ses_feedback_events')==count(setup,'ses_feedback_review')==1


def test_failed_commit_cannot_ack_and_rolls_back(setup,signer):
    connect,trusted,cipher=setup
    class CommitFailure(sqlite3.Connection):
        def commit(self):raise sqlite3.OperationalError('private-secret-commit')
    con=connect()
    try:path=con.execute('PRAGMA database_list').fetchone()[2]
    finally:con.close()
    def failing():
        con=sqlite3.connect(path,factory=CommitFailure);con.row_factory=sqlite3.Row
        return con
    with TestClient(http.create_app(trusted,cipher,failing,clock=lambda:NOW)) as c:
        response=c.post('/sns/feedback',content=signed(signer,event()))
        assert response.status_code==503 and response.content==b''
    assert count(setup,'ses_feedback_events')==count(setup,'mail_recipient_blocks')==0


@pytest.mark.parametrize('body,headers,status',[
    (b'',{},400),(b'x'*131073,{},413),(b'x',{'content-length':'131073'},413),
    (b'x',{'content-length':'private'},400),(b'x',{'content-encoding':'gzip'},415),
])
def test_stream_and_header_bounds_before_db(setup,body,headers,status):
    def forbidden():pytest.fail('Rejected bodies must not access DB')
    _,trusted,cipher=setup
    with TestClient(http.create_app(trusted,cipher,forbidden)) as c:
        response=c.post('/sns/feedback',content=body,headers=headers)
        assert response.status_code==status and response.content==b''


def test_chunked_oversize_is_rejected_without_trusting_content_length(setup):
    def forbidden():pytest.fail('Oversize stream must not access DB')
    _,trusted,cipher=setup
    with TestClient(http.create_app(trusted,cipher,forbidden)) as c:
        assert c.post('/sns/feedback',content=iter([b'x'*65536,b'x'*65537])).status_code==413


def test_http_capacity_rejects_parallel_requests_without_second_db_connection(setup,signer):
    from concurrent.futures import ThreadPoolExecutor
    connect,trusted,cipher=setup;entered=threading.Event();release=threading.Event();calls=[]
    def delayed():
        calls.append(1);entered.set()
        if not release.wait(5):raise RuntimeError('test barrier timed out')
        return connect()
    with TestClient(http.create_app(trusted,cipher,delayed,clock=lambda:NOW,max_inflight=1)) as c:
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending=pool.submit(c.post,'/sns/feedback',content=signed(signer,event()))
            try:
                assert entered.wait(5)
                assert c.post('/sns/feedback',content=signed(signer,event())).status_code==503
                assert len(calls)==1
            finally:release.set()
            assert pending.result(timeout=5).status_code==204


def test_incomplete_body_times_out_before_database_access(setup):
    import anyio
    def forbidden():pytest.fail('Incomplete body must not access DB')
    _,trusted,cipher=setup
    app=http.create_app(trusted,cipher,forbidden,body_timeout=1)
    sent=[];reads=[]
    async def incoming():
        if not reads:
            reads.append(1)
            return {'type':'http.request','body':b'x','more_body':True}
        await anyio.Event().wait()
    async def outgoing(message):sent.append(message)
    scope={'type':'http','asgi':{'version':'3.0'},'http_version':'1.1','method':'POST',
           'scheme':'https','path':'/sns/feedback','raw_path':b'/sns/feedback',
           'query_string':b'','root_path':'','headers':[],'server':('test',443),'client':('test',123)}
    anyio.run(app,scope,incoming,outgoing)
    assert next(m for m in sent if m['type']=='http.response.start')['status']==408
