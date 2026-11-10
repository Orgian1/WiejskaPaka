import json
import os
from dataclasses import replace
from datetime import datetime,timezone
import pytest
from backend import ses_feedback_config as config,mail_suppression as blocks
from backend.reset_mail_queue import transaction
from tests.test_sns_pinned_notification import signer,make_signer,envelope,NOW,TOPIC
from tests.test_ses_feedback import con,event,SOURCE


def document(pin):
    return {'format':1,'topic_arn':TOPIC,'source_arn':SOURCE,'max_age_seconds':86400,
        'pins':[{'certificate_url':pin.certificate_url,'certificate_pem':pin.certificate_pem.decode()}]}


def raw_event(signer,**changes):return json.dumps(envelope(signer[0],json.dumps(event()),**changes))


def test_disabled_reads_no_files_or_network(monkeypatch):
    monkeypatch.setattr(config,'load_file',lambda *a,**kw:pytest.fail('File read'))
    assert config.load_config({'WP_SES_FEEDBACK_CONFIG_FILE':'private-placeholder'}) is None


def test_loaded_configuration_applies_verified_event_without_exposing_pin(signer,con):
    trusted=config.decode(json.dumps(document(signer[1])),now=NOW)
    assert 'BEGIN CERTIFICATE' not in repr(trusted)
    with transaction(con):assert config.apply(con,raw_event(signer),trusted,now=NOW)=='APPLIED'
    with transaction(con):assert config.apply(con,raw_event(signer),trusted,now=NOW)=='DUPLICATE'
    assert blocks.blocked(con,'buyer@example.invalid')


def test_rotation_accepts_both_approved_signers_and_rejects_unknown_pin(signer,con):
    new_key,new_pin=make_signer();new_pin=replace(new_pin,certificate_url=new_pin.certificate_url.replace('synthetic','rotated'))
    doc=document(signer[1]);doc['pins']+=document(new_pin)['pins']
    trusted=config.decode(json.dumps(doc),now=NOW)
    with transaction(con):assert config.apply(con,raw_event(signer),trusted,now=NOW)=='APPLIED'
    rotated=json.dumps(envelope(new_key,json.dumps(event()),SigningCertURL=new_pin.certificate_url,
        MessageId='aaaaaaaa-1234-1234-1234-123456789abc'))
    with transaction(con):assert config.apply(con,rotated,trusted,now=NOW)=='APPLIED'
    unexpected=raw_event(signer,SigningCertURL=signer[1].certificate_url.replace('synthetic','unapproved'))
    with pytest.raises(ValueError,match='INPUT_REJECTED'):
        with transaction(con):config.apply(con,unexpected,trusted,now=NOW)
    wrong_topic=raw_event(signer,TopicArn=TOPIC+'-other')
    with pytest.raises(ValueError,match='INPUT_REJECTED'):
        with transaction(con):config.apply(con,wrong_topic,trusted,now=NOW)


@pytest.mark.parametrize('problem',['duplicate_url','duplicate_certificate','empty','oversized','unknown_key','wrong_account','wrong_region','format_bool','no_current_cert'])
def test_malformed_or_untrusted_configuration_rejected(signer,problem):
    doc=document(signer[1]);now=NOW
    if problem=='duplicate_url':doc['pins']*=2
    if problem=='duplicate_certificate':
        item=dict(doc['pins'][0]);item['certificate_url']=item['certificate_url'].replace('synthetic','other');doc['pins'].append(item)
    if problem=='empty':doc['pins']=[]
    if problem=='oversized':doc['pins']*=5
    if problem=='unknown_key':doc['verified']=True
    if problem=='wrong_account':doc['source_arn']=SOURCE.replace('123456789012','999999999999')
    if problem=='wrong_region':doc['source_arn']=SOURCE.replace('eu-north-1','eu-west-1')
    if problem=='format_bool':doc['format']=True
    if problem=='no_current_cert':now=NOW+9*86400
    with pytest.raises(ValueError,match='^SES_FEEDBACK_CONFIGURATION_REJECTED$'):
        config.decode(json.dumps(doc),now=now)


def test_duplicate_json_and_size_limits_rejected():
    for raw in ('{"format":1,"format":1}','x'*98305):
        with pytest.raises(ValueError,match='CONFIGURATION_REJECTED'):config.decode(raw,now=NOW)


@pytest.mark.skipif(os.name!='posix',reason='Protected external POSIX configuration')
def test_private_file_and_optin_configuration(signer,tmp_path):
    path=tmp_path/'pins.json';path.write_text(json.dumps(document(signer[1])));path.chmod(0o600)
    env={'WP_ENABLE_SES_FEEDBACK_CONFIG':'1','WP_SES_FEEDBACK_CONFIG_FILE':str(path)}
    loaded=config.load_config(env,root=tmp_path/'repository',now=NOW)
    assert loaded.topic_arn==TOPIC and len(loaded.pins)==1
    path.chmod(0o644)
    with pytest.raises(ValueError,match='CONFIGURATION_REJECTED'):config.load_config(env,now=NOW)
    path.chmod(0o600)
    with pytest.raises(ValueError,match='CONFIGURATION_REJECTED'):config.load_file(path,root=tmp_path,now=NOW)
    link=tmp_path/'link.json';link.symlink_to(path)
    with pytest.raises(ValueError,match='CONFIGURATION_REJECTED'):config.load_file(link,now=NOW)
    missing=tmp_path/'missing.json'
    with pytest.raises(ValueError,match='CONFIGURATION_REJECTED'):config.load_file(missing,now=NOW)
    assert not missing.exists()


@pytest.mark.skipif(os.name!='posix',reason='Atomic protected POSIX configuration')
def test_atomic_rotation_produces_new_snapshot_and_keeps_old_config_immutable(signer,tmp_path):
    path=tmp_path/'pins.json';path.write_text(json.dumps(document(signer[1])));path.chmod(0o600)
    before=config.load_file(path,now=NOW)
    _,new_pin=make_signer();new_pin=replace(new_pin,certificate_url=new_pin.certificate_url.replace('synthetic','rotated'))
    doc=document(signer[1]);doc['pins']+=document(new_pin)['pins']
    replacement=tmp_path/'new.json';replacement.write_text(json.dumps(doc));replacement.chmod(0o600)
    os.replace(replacement,path)
    after=config.load_file(path,now=NOW)
    assert len(before.pins)==1 and len(after.pins)==2


def test_file_errors_are_redacted(monkeypatch):
    def fail(*a,**kw):raise OSError('synthetic-private-path-and-content')
    monkeypatch.setattr(config,'load_file',fail)
    with pytest.raises(ValueError,match='^SES_FEEDBACK_CONFIGURATION_REJECTED$'):
        config.load_config({'WP_ENABLE_SES_FEEDBACK_CONFIG':'1','WP_SES_FEEDBACK_CONFIG_FILE':'private'},now=NOW)


@pytest.mark.skipif(os.name!='posix',reason='Protected external POSIX configuration')
def test_checker_uses_real_protected_configuration_without_exposing_identifiers(signer,tmp_path):
    from scripts.check_ses_feedback_configuration import check
    path=tmp_path/'pins.json';path.write_text(json.dumps(document(signer[1])));path.chmod(0o600)
    env={'WP_ENABLE_SES_FEEDBACK_CONFIG':'1','WP_SES_FEEDBACK_CONFIG_FILE':str(path)}
    result=check(env,now=NOW)
    assert result=={'status':'CONFIGURATION_VALID','pins':1}
    assert 'arn:' not in str(result) and str(path) not in str(result)
    path.write_text('synthetic-private-malformed-document')
    assert check(env,now=NOW)=={'status':'CONFIGURATION_REJECTED'}


def test_checker_default_and_error_output_are_fixed(monkeypatch,capsys):
    from scripts import check_ses_feedback_configuration as cli
    assert cli.check({})=={'status':'DISABLED'}
    def fail(*a,**kw):raise ValueError('synthetic-private-path-and-account')
    monkeypatch.setattr(cli,'load_config',fail)
    assert cli.main()==1
    assert capsys.readouterr().out.strip()=='{"status": "CONFIGURATION_REJECTED"}'
