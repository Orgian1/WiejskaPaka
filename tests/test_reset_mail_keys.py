"""Private synthetic key files only; no real credentials or delivery."""
import base64
import json
import os
from pathlib import Path
import sqlite3

import pytest
from backend import reset_mail_keys as loader,reset_mail_queue as queue,password_reset as reset

B64=base64.b64encode(b'a'*32).decode('ascii')
OTHER=base64.b64encode(b'b'*32).decode('ascii')
POSIX=pytest.mark.skipif(os.name!='posix',reason='private POSIX key-file permissions required')


def document():return {'format':1,'active':'v1','keys':{'v1':B64}}


def write(path,obj):
    path.write_text(json.dumps(obj));path.chmod(0o600);return path


def test_disabled_config_never_reads_file(monkeypatch):
    def forbidden(*a,**kw):pytest.fail('disabled key loader must not read a file')
    monkeypatch.setattr(loader,'load_keys',forbidden)
    assert loader.load_config({'WP_MAIL_QUEUE_KEYS_FILE':'private path'}) is None
    assert loader.load_config({'WP_ENABLE_MAIL_QUEUE':'0'}) is None


@pytest.mark.parametrize('config',[{'WP_ENABLE_MAIL_QUEUE':'1'},
 {'WP_ENABLE_MAIL_QUEUE':'1','WP_MAIL_QUEUE_KEYS_FILE':'private-secret-relative-path'}])
def test_invalid_enabled_config_is_redacted(config):
    with pytest.raises(ValueError,match='^MAIL_QUEUE_KEYS_REJECTED$') as caught:loader.load_config(config)
    assert 'private-secret' not in str(caught.value) and caught.value.__cause__ is None


@POSIX
def test_private_file_is_loaded_only_by_explicit_call_and_never_printed(tmp_path,capsys):
    path=write(tmp_path/'keys.json',document())
    keys=loader.load_config({'WP_ENABLE_MAIL_QUEUE':'1','WP_MAIL_QUEUE_KEYS_FILE':str(path)})
    assert keys.active=='v1' and B64 not in repr(keys)
    out=capsys.readouterr();assert not out.out and not out.err
    assert json.loads(path.read_text())==document()


@POSIX
@pytest.mark.parametrize('mode',[0o644,0o640,0o604,0o666])
def test_public_or_group_permissions_are_rejected(tmp_path,mode):
    path=write(tmp_path/'keys.json',document());path.chmod(mode)
    with pytest.raises(ValueError,match='^MAIL_QUEUE_KEYS_REJECTED$'):loader.load_keys(path)


@POSIX
def test_read_only_private_key_file_is_supported(tmp_path):
    path=write(tmp_path/'keys.json',document());path.chmod(0o400)
    assert loader.load_keys(path).active=='v1'


@POSIX
def test_symlink_directory_fifo_and_project_local_files_are_rejected(tmp_path):
    path=write(tmp_path/'keys.json',document());link=tmp_path/'link';link.symlink_to(path)
    fifo=tmp_path/'fifo';os.mkfifo(fifo)
    for candidate in (link,tmp_path,fifo):
        with pytest.raises(ValueError,match='^MAIL_QUEUE_KEYS_REJECTED$'):loader.load_keys(candidate)
    with pytest.raises(ValueError,match='^MAIL_QUEUE_KEYS_REJECTED$'):loader.load_keys(path,root=tmp_path)


@POSIX
def test_missing_and_oversized_files_are_rejected(tmp_path):
    with pytest.raises(ValueError,match='^MAIL_QUEUE_KEYS_REJECTED$'):loader.load_keys(tmp_path/'missing')
    path=tmp_path/'large';path.write_bytes(b'x'*(loader.MAX_BYTES+1));path.chmod(0o600)
    with pytest.raises(ValueError,match='^MAIL_QUEUE_KEYS_REJECTED$'):loader.load_keys(path)


@POSIX
@pytest.mark.parametrize('contents',[
 'not-json-private-secret','[]','{}','{"format":1,"format":1,"active":"v1","keys":{}}',
 '{"format":1,"active":"v1","keys":{"v1":"private-secret","v1":"private-secret"}}'])
def test_malformed_or_ambiguous_json_is_rejected(tmp_path,contents):
    path=tmp_path/'keys';path.write_text(contents);path.chmod(0o600)
    with pytest.raises(ValueError,match='^MAIL_QUEUE_KEYS_REJECTED$'):loader.load_keys(path)


@POSIX
@pytest.mark.parametrize('patch',[
 {'format':True},{'format':2},{'active':'missing'},{'active':None},{'extra':'private-secret'},
 {'keys':{}},{'keys':{'bad key':B64}},{'keys':{'v1':'not-base64-private-secret'}},
 {'keys':{'v1':base64.b64encode(b'short').decode()}},{'keys':{'v1':123}},
 {'keys':{'v1':B64,'v2':B64}},
 {'keys':{'v'+str(i):base64.b64encode(bytes([i])*32).decode() for i in range(9)}}])
def test_invalid_format_version_active_key_and_material_are_rejected(tmp_path,patch):
    obj=document();obj.update(patch);path=write(tmp_path/'keys',obj)
    with pytest.raises(ValueError,match='^MAIL_QUEUE_KEYS_REJECTED$'):loader.load_keys(path)


@POSIX
def test_rotation_and_reopen_decrypt_an_existing_queue_payload(tmp_path):
    path=write(tmp_path/'keys',document());old=loader.load_keys(path)
    con=sqlite3.connect(':memory:');con.row_factory=sqlite3.Row
    try:
        con.executescript('CREATE TABLE users(id INTEGER PRIMARY KEY,email TEXT,password_hash TEXT);'+reset.SCHEMA_SQLITE+queue.SCHEMA)
        con.execute("INSERT INTO users VALUES(1,'synthetic@example.invalid','synthetic-version')");con.commit()
        with queue.transaction(con):queue.issue(con,old,'synthetic@example.invalid',now=1792396800)
        write(path,{'format':1,'active':'v2','keys':{'v1':B64,'v2':OTHER}})
        rotated=loader.load_keys(path)
        with queue.transaction(con):lease=queue.claim(con,now=1792396800)
        with queue.transaction(con):delivery=queue.start(con,rotated,lease,now=1792396800)
        assert delivery.recipient=='synthetic@example.invalid' and rotated.active=='v2'
    finally:con.close()


@POSIX
def test_file_owned_by_another_user_is_rejected(tmp_path,monkeypatch):
    from types import SimpleNamespace
    path=write(tmp_path/'keys',document())
    actual=os.fstat
    def other_owner(fd):
        info=actual(fd)
        return SimpleNamespace(st_mode=info.st_mode,st_uid=os.getuid()+1,st_size=info.st_size)
    monkeypatch.setattr(loader.os,'fstat',other_owner)
    with pytest.raises(ValueError,match='^MAIL_QUEUE_KEYS_REJECTED$'):loader.load_keys(path)


@pytest.mark.skipif(os.name=='posix',reason='explicit non-POSIX permission refusal')
def test_non_posix_key_loading_fails_closed(tmp_path):
    path=tmp_path/'keys';path.write_text(json.dumps(document()))
    with pytest.raises(ValueError,match='^MAIL_QUEUE_KEYS_REJECTED$'):loader.load_keys(path)
