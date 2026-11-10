import pytest
from backend import ses_feedback_archive as archive,ses_review_key_check as check
from backend.reset_mail_queue import transaction
from tests.test_ses_feedback_archive import setup,receive
from tests.test_ses_feedback import con,event,signed
from tests.test_sns_pinned_notification import signer,NOW


def seed(setup,signer):
    con,_,_=setup
    with transaction(con):receive(setup,signed(signer,event(bounce_type='Undetermined')))


def test_checks_real_ciphertext_with_read_only_database_and_no_data_changes(setup,signer):
    con,_,cipher=setup;seed(setup,signer)
    before=con.total_changes
    con.execute('PRAGMA query_only=ON');con.execute('BEGIN')
    try:assert check.check_retained(con,cipher,now=NOW)=={'status':'RETAINED_KEYS_VALID','checked':1}
    finally:con.rollback()
    assert con.total_changes==before


@pytest.mark.parametrize('problem',['missing-key','wrong-material','tampered-ciphertext','tampered-expiry'])
def test_checks_material_not_only_matching_key_identifier(setup,signer,problem):
    con,_,cipher=setup;seed(setup,signer)
    if problem=='missing-key':cipher=archive.ArchiveCipher({'new':b'n'*32},'new')
    elif problem=='wrong-material':cipher=archive.ArchiveCipher({'review-v1':b'w'*32},'review-v1')
    else:
        with transaction(con):
            if problem=='tampered-ciphertext':con.execute("UPDATE ses_feedback_review SET payload=?",(b'invalid',))
            else:con.execute('UPDATE ses_feedback_review SET expires_at=expires_at+1')
    with transaction(con):
        with pytest.raises(ValueError,match='^SES_RETAINED_KEYS_REJECTED$'):check.check_retained(con,cipher,now=NOW)


def test_rotated_snapshot_covers_old_records_and_active_key_can_differ(setup,signer):
    con,_,_=setup;seed(setup,signer)
    proposed=archive.ArchiveCipher({'review-v1':b'k'*32,'new':b'n'*32},'new')
    with transaction(con):assert check.check_retained(con,proposed,now=NOW)['checked']==1
    assert proposed.active=='new'


def test_expired_live_record_does_not_require_retired_material(setup,signer):
    con,_,_=setup;seed(setup,signer)
    replacement=archive.ArchiveCipher({'new':b'n'*32},'new')
    with transaction(con):
        assert check.check_retained(con,replacement,now=NOW+604800)=={'status':'RETAINED_KEYS_VALID','checked':0}
    assert con.execute('SELECT count(*) FROM ses_feedback_review').fetchone()[0]==1


def test_inventory_limit_fails_before_decrypting_large_payloads(setup,signer,monkeypatch):
    con,_,cipher=setup;seed(setup,signer)
    with transaction(con):
        receive(setup,signed(signer,event(bounce_type='Undetermined'),MessageId='22345678-1234-1234-1234-123456789abc'))
    def forbidden(*args):pytest.fail('Over-limit inventory must not decrypt')
    monkeypatch.setattr(cipher,'open',forbidden)
    with transaction(con):
        with pytest.raises(ValueError,match='^SES_RETAINED_KEYS_REJECTED$'):
            check.check_retained(con,cipher,now=NOW,max_records=1)


def test_empty_archive_is_valid_but_no_transaction_is_rejected(setup):
    con,_,cipher=setup
    with pytest.raises(ValueError,match='^SES_RETAINED_KEYS_REJECTED$'):check.check_retained(con,cipher,now=NOW)
    with transaction(con):assert check.check_retained(con,cipher,now=NOW)['checked']==0
