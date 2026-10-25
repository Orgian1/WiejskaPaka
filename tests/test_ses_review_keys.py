import base64
import json
import os
import pytest
from backend import ses_review_keys as keys
from backend.ses_feedback_archive import ArchiveCipher
from scripts import check_ses_review_keys as checker


def document(**changes):
    obj={'format':1,'purpose':keys.PURPOSE,'active':'archive-1',
         'keys':{'archive-1':base64.b64encode(b'a'*32).decode()}}
    obj.update(changes)
    return obj


def raw(**changes):return json.dumps(document(**changes)).encode()


def row(cipher):
    import hashlib
    data=b'synthetic-review-private-body'
    item={'event_key':'e'*64,'raw_hash':hashlib.sha256(data).hexdigest(),
          'key_id':cipher.active,'received_at':100,'expires_at':3700}
    item['payload']=cipher.seal(item,data)
    return item,data


def test_loaded_keys_really_encrypt_decrypt_without_exposing_material():
    cipher=keys.decode(raw());item,data=row(cipher)
    assert isinstance(cipher,ArchiveCipher) and cipher.open(item)==data
    assert b'private-body' not in item['payload']
    assert 'aaaa' not in repr(cipher) and base64.b64encode(b'a'*32).decode() not in repr(cipher)


@pytest.mark.parametrize('change',[
    {'format':True},{'purpose':'password-reset'},{'active':'missing'},{'keys':{}},
    {'keys':{'bad!':'YQ=='}},{'keys':{'archive-1':base64.b64encode(b'a'*31).decode()}},
    {'keys':{'archive-1':base64.b64encode(b'a'*32).decode()+'='}},
    {'keys':{'archive-1':base64.b64encode(b'a'*32).decode(),'archive-2':base64.b64encode(b'a'*32).decode()}},
    {'keys':{'k'+str(i):base64.b64encode(bytes([i])*32).decode() for i in range(9)}},
    {'unrecognized':'private-secret'},
])
def test_invalid_or_accidentally_reused_key_documents_rejected(change):
    with pytest.raises(ValueError,match='^SES_REVIEW_KEYS_REJECTED$'):keys.decode(raw(**change))


@pytest.mark.parametrize('value',[b'[]',b'{"format":1,"format":1}',b'{"value":NaN}',b'x'*16385],
                         ids=['array','duplicate','constant','oversize'])
def test_bounded_unambiguous_json(value):
    with pytest.raises(ValueError,match='^SES_REVIEW_KEYS_REJECTED$'):keys.decode(value)


def test_queue_format_is_not_an_archive_key_file():
    obj=document();obj.pop('purpose')
    with pytest.raises(ValueError,match='^SES_REVIEW_KEYS_REJECTED$'):keys.decode(json.dumps(obj))


def test_disabled_means_no_file_reads(monkeypatch):
    def forbidden(*args,**kwargs):pytest.fail('Disabled loader must not read keys')
    monkeypatch.setattr(keys,'load_file',forbidden)
    assert keys.load_config({'WP_SES_REVIEW_KEYS_FILE':'private'}) is None
    assert checker.check({})=={'status':'DISABLED'}


@pytest.mark.skipif(os.name!='posix',reason='POSIX permission boundary')
def test_private_file_atomic_rotation_preserves_old_snapshot(tmp_path):
    path=tmp_path/'archive.json';path.write_bytes(raw());path.chmod(0o600)
    env={'WP_ENABLE_SES_REVIEW_KEYS':'1','WP_SES_REVIEW_KEYS_FILE':str(path)}
    old=keys.load_config(env);item,data=row(old)
    next_doc=document(active='archive-2',keys={'archive-1':base64.b64encode(b'a'*32).decode(),
                                            'archive-2':base64.b64encode(b'b'*32).decode()})
    pending=tmp_path/'next.json';pending.write_text(json.dumps(next_doc));pending.chmod(0o600)
    os.replace(pending,path)
    new=keys.load_config(env)
    assert old.active=='archive-1' and new.active=='archive-2'
    assert new.open(item)==old.open(item)==data
    fresh,_=row(new)
    assert fresh['key_id']=='archive-2'
    with pytest.raises(ValueError,match='DECRYPTION_REJECTED'):old.open(fresh)
    assert checker.check(env)=={'status':'KEYS_VALID'}


@pytest.mark.skipif(os.name!='posix',reason='POSIX permission boundary')
@pytest.mark.parametrize('problem',['public','symlink','internal','missing','directory','oversize','fifo'])
def test_unsafe_files_are_rejected_without_creation(tmp_path,problem):
    root=tmp_path/'project';root.mkdir()
    path=tmp_path/'private.json';path.write_bytes(raw());path.chmod(0o600)
    if problem=='public':path.chmod(0o644)
    elif problem=='symlink':
        link=tmp_path/'link';link.symlink_to(path);path=link
    elif problem=='internal':
        path=root/'inside.json';path.write_bytes(raw());path.chmod(0o600)
    elif problem=='missing':path=tmp_path/'absent-private-secret'
    elif problem=='directory':path=tmp_path
    elif problem=='oversize':path.write_bytes(b'x'*16385)
    elif problem=='fifo':
        path.unlink();os.mkfifo(path,0o600)
    with pytest.raises(ValueError,match='^SES_REVIEW_KEYS_REJECTED$'):keys.load_file(path,root=root)
    if problem=='missing':assert not path.exists()


def test_checker_redacts_errors_and_does_not_approve_missing_configuration(capsys,monkeypatch):
    env={'WP_ENABLE_SES_REVIEW_KEYS':'1','WP_SES_REVIEW_KEYS_FILE':'private-secret-path'}
    assert checker.check(env)=={'status':'KEYS_REJECTED'}
    monkeypatch.setattr(checker,'load_config',lambda *a: (_ for _ in ()).throw(RuntimeError('private-secret')))
    assert checker.main()==1
    assert json.loads(capsys.readouterr().out)=={'status':'KEYS_REJECTED'}
