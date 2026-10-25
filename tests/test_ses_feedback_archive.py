import json
import pytest
from backend import ses_feedback_archive as archive,ses_feedback_config
from backend.reset_mail_queue import transaction
from tests.test_ses_feedback import con,event,signed,SOURCE
from tests.test_sns_pinned_notification import signer,NOW


@pytest.fixture
def setup(con,signer):
    con.executescript(archive.SCHEMA_SQLITE)
    config=ses_feedback_config.FeedbackConfig(signer[1].topic_arn,SOURCE,(signer[1],))
    cipher=archive.ArchiveCipher({'review-v1':b'k'*32},'review-v1')
    return con,config,cipher


def receive(setup,raw,**kwargs):
    con,config,cipher=setup
    return archive.receive(con,raw,config,cipher,now=NOW,**kwargs)


def test_review_is_encrypted_recoverable_and_deduplicated(setup,signer):
    con,_,cipher=setup;raw=signed(signer,event(bounce_type='Undetermined'))
    with transaction(con):assert receive(setup,raw)=='REVIEW'
    row=con.execute('SELECT * FROM ses_feedback_review').fetchone()
    assert cipher.open(row)==raw.encode()
    assert b'buyer@example.invalid' not in row['payload']
    assert b'Undetermined' not in row['payload']
    assert 'kkkk' not in repr(cipher)
    with transaction(con):assert receive(setup,raw)=='DUPLICATE'
    assert con.execute('SELECT count(*) FROM ses_feedback_review').fetchone()[0]==1


@pytest.mark.parametrize('kind,extra,result',[
    ('Bounce',{},'APPLIED'),('Delivery',{},'IGNORED'),
    ('Bounce',{'bounce_type':'Transient'},'IGNORED'),
    ('Complaint',{'complaint_type':'auth-failure'},'REVIEW')])
def test_only_authenticated_review_payloads_are_archived(setup,signer,kind,extra,result):
    con,_,_=setup
    with transaction(con):assert receive(setup,signed(signer,event(kind,**extra)))==result
    assert con.execute('SELECT count(*) FROM ses_feedback_review').fetchone()[0]==int(result=='REVIEW')


@pytest.mark.parametrize('problem',['signature','stale','unapproved','oversize'])
def test_untrusted_or_stale_inputs_never_enter_archive(setup,signer,problem):
    con,_,_=setup;raw=signed(signer,event(bounce_type='Undetermined'))
    if problem=='signature':raw=raw.replace('Undetermined','Permanent')
    if problem=='stale':
        from tests.test_sns_pinned_notification import envelope
        raw=json.dumps(envelope(signer[0],json.dumps(event()),Timestamp='2020-01-01T00:00:00Z'))
    if problem=='unapproved':raw=raw.replace('synthetic.pem','unapproved.pem')
    if problem=='oversize':raw='x'*131073
    with transaction(con):
        with pytest.raises(ValueError,match='^SES_REVIEW_RECEIVE_REJECTED$'):receive(setup,raw)
    assert con.execute('SELECT count(*) FROM ses_feedback_events').fetchone()[0]==0
    assert con.execute('SELECT count(*) FROM ses_feedback_review').fetchone()[0]==0


def test_full_archive_rolls_back_journal_even_if_caller_catches_failure(setup,signer):
    con,_,_=setup;raw=signed(signer,event(bounce_type='Undetermined'))
    with transaction(con):assert receive(setup,raw,max_records=1)=='REVIEW'
    second=signed(signer,event(bounce_type='Undetermined'),MessageId='22345678-1234-1234-1234-123456789abc')
    with transaction(con):
        with pytest.raises(ValueError,match='RECEIVE_REJECTED'):receive(setup,second,max_records=1)
    assert con.execute('SELECT count(*) FROM ses_feedback_events').fetchone()[0]==1
    with transaction(con):assert receive(setup,second,max_records=2)=='REVIEW'


def test_encryption_failure_leaves_no_partial_journal(setup,signer,monkeypatch):
    con,_,cipher=setup
    def broken(*args):raise RuntimeError('private-recipient-secret')
    monkeypatch.setattr(cipher,'seal',broken)
    with transaction(con):
        with pytest.raises(ValueError,match='^SES_REVIEW_RECEIVE_REJECTED$'):
            receive(setup,signed(signer,event(bounce_type='Undetermined')))
    assert con.execute('SELECT count(*) FROM ses_feedback_events').fetchone()[0]==0


@pytest.mark.parametrize('field,value',[('payload',b'bad'),('event_key','0'*64),
    ('raw_hash','1'*64),('expires_at',NOW+1),('key_id','unknown')])
def test_ciphertext_and_metadata_are_authenticated(setup,signer,field,value):
    con,_,cipher=setup
    with transaction(con):receive(setup,signed(signer,event(bounce_type='Undetermined')))
    row=dict(con.execute('SELECT * FROM ses_feedback_review').fetchone());row[field]=value
    with pytest.raises(ValueError,match='^SES_REVIEW_DECRYPTION_REJECTED$'):cipher.open(row)


def test_rotation_and_expiry_are_explicit(setup,signer):
    con,config,old=setup;raw=signed(signer,event(bounce_type='Undetermined'))
    with transaction(con):receive(setup,raw,retention_seconds=3600)
    row=con.execute('SELECT * FROM ses_feedback_review').fetchone()
    rotated=archive.ArchiveCipher({'review-v1':b'k'*32,'review-v2':b'n'*32},'review-v2')
    assert rotated.open(row)==raw.encode()
    with transaction(con):assert archive.purge_expired(con,now=NOW+3599)==0
    with transaction(con):assert archive.purge_expired(con,now=NOW+3600)==1
    assert con.execute('SELECT count(*) FROM ses_feedback_events').fetchone()[0]==1


def test_outer_rollback_removes_both_journal_and_archive(setup,signer):
    con,_,_=setup
    with pytest.raises(RuntimeError):
        with transaction(con):
            receive(setup,signed(signer,event(bounce_type='Undetermined')))
            raise RuntimeError('cancel')
    assert con.execute('SELECT count(*) FROM ses_feedback_events').fetchone()[0]==0
    assert con.execute('SELECT count(*) FROM ses_feedback_review').fetchone()[0]==0


def test_expired_rows_free_capacity_before_next_review(setup,signer):
    con,config,cipher=setup
    raw=signed(signer,event(bounce_type='Undetermined'))
    with transaction(con):receive(setup,raw,max_records=1,retention_seconds=3600)
    second=signed(signer,event(bounce_type='Undetermined'),MessageId='22345678-1234-1234-1234-123456789abc')
    with transaction(con):
        assert archive.receive(con,second,config,cipher,now=NOW+3600,max_records=1,retention_seconds=3600)=='REVIEW'
    assert con.execute('SELECT count(*) FROM ses_feedback_review').fetchone()[0]==1
    assert con.execute('SELECT count(*) FROM ses_feedback_events').fetchone()[0]==2


def test_existing_review_can_be_archived_without_extending_original_retention(setup,signer):
    con,config,cipher=setup;raw=signed(signer,event(bounce_type='Undetermined'))
    with transaction(con):assert ses_feedback_config.apply(con,raw,config,now=NOW)=='REVIEW'
    with transaction(con):
        assert archive.receive(con,raw,config,cipher,now=NOW+60,retention_seconds=3600)=='DUPLICATE'
    row=con.execute('SELECT * FROM ses_feedback_review').fetchone()
    assert row['received_at']==NOW and row['expires_at']==NOW+3600
    with transaction(con):archive.purge_expired(con,now=NOW+3600)
    with transaction(con):
        assert archive.receive(con,raw,config,cipher,now=NOW+3600,retention_seconds=3600)=='DUPLICATE'
    assert con.execute('SELECT count(*) FROM ses_feedback_review').fetchone()[0]==0


def test_insert_failure_preserves_other_caller_work_but_not_partial_event(setup,signer):
    con,_,_=setup
    con.execute('CREATE TABLE caller_work(id INTEGER)')
    con.execute("CREATE TRIGGER reject_archive BEFORE INSERT ON ses_feedback_review BEGIN SELECT RAISE(ABORT,'private'); END")
    with transaction(con):
        con.execute('INSERT INTO caller_work VALUES(1)')
        with pytest.raises(ValueError,match='^SES_REVIEW_RECEIVE_REJECTED$'):
            receive(setup,signed(signer,event(bounce_type='Undetermined')))
    assert con.execute('SELECT count(*) FROM caller_work').fetchone()[0]==1
    assert con.execute('SELECT count(*) FROM ses_feedback_events').fetchone()[0]==0


@pytest.mark.parametrize('changes',[{'max_records':True},{'max_records':0},
    {'retention_seconds':True},{'retention_seconds':2592001}])
def test_invalid_policy_never_registers_event(setup,signer,changes):
    con,_,_=setup
    with transaction(con):
        with pytest.raises(ValueError,match='^SES_REVIEW_CONTEXT_REJECTED$'):
            receive(setup,signed(signer,event()),**changes)
    assert con.execute('SELECT count(*) FROM ses_feedback_events').fetchone()[0]==0


def test_no_implicit_transaction_or_keys(setup,signer):
    with pytest.raises(ValueError,match='TRANSACTION_REQUIRED'):
        receive(setup,signed(signer,event()))
    with pytest.raises(ValueError,match='^SES_REVIEW_KEYS_REJECTED$'):
        archive.ArchiveCipher({},'missing')


def test_rotated_key_is_used_for_new_event_and_wrong_key_cannot_open(setup,signer):
    con,config,_=setup
    cipher=archive.ArchiveCipher({'new':b'n'*32},'new')
    raw=signed(signer,event(bounce_type='Undetermined'))
    with transaction(con):assert archive.receive(con,raw,config,cipher,now=NOW)=='REVIEW'
    row=con.execute('SELECT * FROM ses_feedback_review').fetchone()
    assert row['key_id']=='new' and cipher.open(row)==raw.encode()
    wrong=archive.ArchiveCipher({'new':b'w'*32},'new')
    with pytest.raises(ValueError,match='^SES_REVIEW_DECRYPTION_REJECTED$'):wrong.open(row)
    corrupted=dict(row);payload=bytearray(row['payload']);payload[-1]^=1;corrupted['payload']=bytes(payload)
    with pytest.raises(ValueError,match='^SES_REVIEW_DECRYPTION_REJECTED$'):cipher.open(corrupted)
