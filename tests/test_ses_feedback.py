import json
import sqlite3
import pytest
from backend import ses_feedback as feedback,mail_suppression as blocks
from backend.reset_mail_queue import transaction
from tests.test_sns_pinned_notification import signer,envelope,NOW

SOURCE='arn:aws:ses:eu-north-1:123456789012:identity/wiejskapaka.pl'


@pytest.fixture
def con():
    db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row
    db.executescript(feedback.SCHEMA_SQLITE+blocks.SCHEMA_SQLITE)
    yield db
    db.close()


def event(kind='Bounce',*,bounce_type='Permanent',complaint_type='abuse',target='buyer@example.invalid'):
    obj={'notificationType':kind,'mail':{'sourceArn':SOURCE,'sendingAccountId':'123456789012',
        'messageId':'synthetic-ses-id','destination':['buyer@example.invalid']}}
    if kind=='Bounce':obj['bounce']={'bounceType':bounce_type,'bouncedRecipients':[{'emailAddress':target}]}
    if kind=='Complaint':obj['complaint']={'complaintFeedbackType':complaint_type,'complainedRecipients':[{'emailAddress':target}]}
    return obj


def signed(signer,obj,**changes):return json.dumps(envelope(signer[0],json.dumps(obj),**changes))


def apply(con,signer,obj,**changes):
    return feedback.apply(con,signed(signer,obj,**changes),signer[1],source_arn=SOURCE,now=NOW)


@pytest.mark.parametrize('kind',['Bounce','Complaint'])
def test_valid_feedback_atomic_idempotent_and_private(con,signer,kind):
    obj=event(kind)
    with transaction(con):assert apply(con,signer,obj)=='APPLIED'
    with transaction(con):assert apply(con,signer,obj)=='DUPLICATE'
    assert blocks.blocked(con,'buyer@example.invalid')
    row=con.execute('SELECT * FROM ses_feedback_events').fetchone()
    assert '@' not in str(tuple(row)) and 'buyer' not in str(tuple(row))
    assert con.execute('SELECT count(*) FROM ses_feedback_events').fetchone()[0]==1


@pytest.mark.parametrize('kind,extra,expected',[
    ('Bounce',{'bounce_type':'Transient'},'IGNORED'),('Bounce',{'bounce_type':'Undetermined'},'REVIEW'),
    ('Complaint',{'complaint_type':'not-spam'},'IGNORED'),('Complaint',{'complaint_type':'auth-failure'},'REVIEW'),
    ('Delivery',{},'IGNORED')])
def test_only_unambiguous_permanent_bounce_and_abuse_complaint_block(con,signer,kind,extra,expected):
    with transaction(con):assert apply(con,signer,event(kind,**extra))==expected
    assert not blocks.blocked(con,'buyer@example.invalid')


@pytest.mark.parametrize('problem',['hidden','multiple','destination_mismatch','wrong_account','wrong_identity','invalid_signature'])
def test_ambiguous_or_untrusted_feedback_never_blocks(con,signer,problem):
    obj=event('Complaint')
    if problem=='hidden':obj['complaint']['complainedRecipients']=[]
    if problem=='multiple':obj['mail']['destination'].append('other@example.invalid')
    if problem=='destination_mismatch':obj['complaint']['complainedRecipients'][0]['emailAddress']='other@example.invalid'
    if problem=='wrong_account':obj['mail']['sendingAccountId']='999999999999'
    if problem=='wrong_identity':obj['mail']['sourceArn']=SOURCE+'-other'
    raw=signed(signer,obj)
    if problem=='invalid_signature':
        outer=json.loads(raw);outer['Message']='modified';raw=json.dumps(outer)
    if problem in ('hidden','multiple'):
        with transaction(con):assert feedback.apply(con,raw,signer[1],source_arn=SOURCE,now=NOW)=='REVIEW'
    else:
        with pytest.raises(ValueError,match='FEEDBACK_REJECTED'):
            with transaction(con):feedback.apply(con,raw,signer[1],source_arn=SOURCE,now=NOW)
        assert con.execute('SELECT count(*) FROM ses_feedback_events').fetchone()[0]==0
    assert con.execute('SELECT count(*) FROM mail_recipient_blocks').fetchone()[0]==0


def test_conflicting_duplicate_and_transaction_rollback(con,signer):
    con.execute('BEGIN IMMEDIATE');assert apply(con,signer,event())=='APPLIED';con.rollback()
    assert not blocks.blocked(con,'buyer@example.invalid')
    with transaction(con):assert apply(con,signer,event())=='APPLIED'
    with pytest.raises(ValueError,match='FEEDBACK_CONFLICT'):
        with transaction(con):apply(con,signer,event('Complaint'))
    assert con.execute('SELECT reason FROM mail_recipient_blocks').fetchone()[0]=='permanent_bounce'


def test_unverified_json_duplicate_members_and_missing_transaction_rejected(con,signer):
    with pytest.raises(ValueError,match='TRANSACTION_REQUIRED'):apply(con,signer,event())
    raw=json.dumps(envelope(signer[0],'{"mail":{},"mail":{}}'))
    with pytest.raises(ValueError,match='FEEDBACK_REJECTED'):
        with transaction(con):feedback.apply(con,raw,signer[1],source_arn=SOURCE,now=NOW)


def test_journal_failure_rolls_back_suppression(con,signer):
    con.execute("CREATE TRIGGER fail_feedback BEFORE INSERT ON ses_feedback_events BEGIN SELECT RAISE(ABORT,'synthetic journal failure'); END")
    with pytest.raises(sqlite3.IntegrityError):
        with transaction(con):apply(con,signer,event())
    assert not blocks.blocked(con,'buyer@example.invalid')
    assert con.execute('SELECT count(*) FROM ses_feedback_events').fetchone()[0]==0
