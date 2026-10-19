"""Encrypted synthetic key backups only; no live secrets, SMTP or DB restore."""
import base64
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from backend import reset_mail_keys as loader, reset_mail_queue as queue
from scripts import mail_queue_key_backup as backup
from tests.test_reset_mail_queue import store, enqueue, NOW


def document(active='v1',keys=None):
    return {'format':1,'active':active,'keys':{k:base64.b64encode(v).decode('ascii')
        for k,v in (keys or {'v1':b'a'*32,'v0':b'b'*32}).items()}}


def write(path,obj):
    path.write_text(json.dumps(obj));path.chmod(0o600);return path


@pytest.fixture
def paths(tmp_path):
    if os.name!='posix':pytest.skip('private POSIX key files required')
    dirs=[tmp_path/name for name in ('live','wrapping','archives','restored')]
    for folder in dirs:folder.mkdir(mode=0o700)
    source=write(dirs[0]/'keys.json',document())
    wrapper=dirs[1]/'backup-key.json';backup.init_backup_key(wrapper)
    return source,wrapper,dirs[2]/'keys.mailkeybackup',dirs[3]/'keys.json'


def test_backup_restore_recovers_pending_job_without_activation(paths,store):
    source,wrapper,archive,destination=paths
    job=enqueue(store)
    row=store[0].execute('SELECT * FROM reset_mail_queue WHERE id=?',(job,)).fetchone()
    expected=store[2].decrypt(row)
    live_before=source.read_bytes()
    assert backup.backup(source,wrapper,archive)=={'encrypted_backup':True}
    raw=archive.read_bytes()
    assert b'a'*32 not in raw and base64.b64encode(b'a'*32) not in raw
    # Later live rotation must not be overwritten by restoring an older copy.
    write(source,document('v2',{'v0':b'b'*32,'v1':b'a'*32,'v2':b'c'*32}))
    rotated=source.read_bytes()
    assert backup.restore(archive,wrapper,destination)=={'restored':True}
    recovered=loader.load_keys(destination)
    assert recovered.active=='v1' and recovered.decrypt(row)==expected
    assert source.read_bytes()==rotated and rotated!=live_before
    after=store[0].execute('SELECT * FROM reset_mail_queue WHERE id=?',(job,)).fetchone()
    assert tuple(after)==tuple(row) and after['state']=='queued' and after['attempts']==0
    assert archive.stat().st_mode&0o777==0o600
    assert destination.stat().st_mode&0o777==0o600


def test_old_archive_survives_wrapping_key_rotation(paths):
    source,wrapper,archive,destination=paths
    backup.backup(source,wrapper,archive)
    obj=json.loads(wrapper.read_text());obj['keys']['backup-v2']=base64.b64encode(b'z'*32).decode()
    obj['active']='backup-v2';write(wrapper,obj)
    assert backup.restore(archive,wrapper,destination)=={'restored':True}
    assert loader.load_keys(destination).active=='v1'
    del obj['keys']['backup-v1'];write(wrapper,obj)
    with pytest.raises(ValueError,match='^MAIL_KEY_BACKUP_REJECTED$'):
        backup.restore(archive,wrapper,destination.with_name('missing-history.json'))
    assert not destination.with_name('missing-history.json').exists()


@pytest.mark.parametrize('damage',['magic','size','key-id','tag','truncate'])
def test_corruption_is_rejected_before_any_plaintext_file(paths,damage):
    source,wrapper,archive,destination=paths;backup.backup(source,wrapper,archive)
    raw=bytearray(archive.read_bytes())
    if damage=='truncate':raw=raw[:10]
    else:raw[{'magic':0,'size':8,'key-id':9,'tag':len(raw)-1}[damage]]^=255
    archive.write_bytes(raw)
    with pytest.raises(ValueError,match='^MAIL_KEY_BACKUP_REJECTED$') as error:
        backup.restore(archive,wrapper,destination)
    assert error.value.__cause__ is None and not destination.exists()
    assert list(destination.parent.iterdir())==[]


def test_wrong_wrapping_key_never_writes_destination(paths):
    source,wrapper,archive,destination=paths;backup.backup(source,wrapper,archive)
    wrapper.unlink();backup.init_backup_key(wrapper)
    with pytest.raises(ValueError,match='^MAIL_KEY_BACKUP_REJECTED$'):
        backup.restore(archive,wrapper,destination)
    assert not destination.exists()


def test_reused_live_key_is_not_an_independent_backup_key(paths):
    source,wrapper,archive,_=paths;write(wrapper,document())
    with pytest.raises(ValueError,match='^MAIL_KEY_BACKUP_REJECTED$'):
        backup.backup(source,wrapper,archive)
    assert not archive.exists()


def test_backup_key_inside_archive_directory_is_rejected(paths):
    source,wrapper,archive,_=paths
    local=archive.parent/'wrapping-key.json';write(local,json.loads(wrapper.read_text()))
    with pytest.raises(ValueError,match='^MAIL_KEY_BACKUP_REJECTED$'):
        backup.backup(source,local,archive)
    assert not archive.exists()


@pytest.mark.parametrize('operation',['init','backup','restore'])
def test_existing_destination_is_never_replaced(paths,operation):
    source,wrapper,archive,destination=paths
    if operation=='init':target=wrapper;call=lambda:backup.init_backup_key(target)
    elif operation=='backup':
        target=archive;target.write_bytes(b'synthetic-preserved');target.chmod(0o600)
        call=lambda:backup.backup(source,wrapper,target)
    else:
        backup.backup(source,wrapper,archive);target=destination
        target.write_bytes(b'synthetic-preserved');target.chmod(0o600)
        call=lambda:backup.restore(archive,wrapper,target)
    before=target.read_bytes()
    with pytest.raises(ValueError,match='^MAIL_KEY_BACKUP_REJECTED$'):call()
    assert target.read_bytes()==before
    assert not list(target.parent.glob('.wp-backup-*'))


@pytest.mark.parametrize('kind',['source','wrapper','archive','parent','symlink','fifo','oversize'])
def test_unsafe_files_and_directories_are_rejected(paths,kind):
    source,wrapper,archive,destination=paths;backup.backup(source,wrapper,archive)
    call=lambda:backup.restore(archive,wrapper,destination)
    if kind=='source':source.chmod(0o644);call=lambda:backup.backup(source,wrapper,archive.with_name('other.mailkeybackup'))
    elif kind=='wrapper':wrapper.chmod(0o644)
    elif kind=='archive':archive.chmod(0o644)
    elif kind=='parent':destination.parent.chmod(0o755)
    elif kind=='symlink':
        other=archive.with_name('real.mailkeybackup');archive.rename(other);archive.symlink_to(other)
    elif kind=='fifo':archive.unlink();os.mkfifo(archive,0o600)
    else:archive.write_bytes(b'x'*(backup.MAX_ARCHIVE+1))
    with pytest.raises(ValueError,match='^MAIL_KEY_BACKUP_REJECTED$'):call()
    assert not destination.exists()


def test_cli_success_and_errors_never_include_private_paths(paths):
    source,wrapper,archive,destination=paths
    command=[sys.executable,'-m','scripts.mail_queue_key_backup']
    result=subprocess.run([*command,'backup','--source',str(source),'--backup-key',str(wrapper),
        '--destination',str(archive)],capture_output=True,text=True,timeout=10)
    assert result.returncode==0 and json.loads(result.stdout)=={'encrypted_backup':True} and not result.stderr
    for args in (['restore','--archive',str(archive),'--backup-key',str(wrapper),
                  '--destination','synthetic-private-relative-path'],['unexpected-synthetic-private-argument']):
        result=subprocess.run([*command,*args],capture_output=True,text=True,timeout=10)
        assert result.returncode!=0 and not result.stdout
        assert result.stderr.strip()=='MAIL_KEY_BACKUP_REJECTED'


@pytest.mark.skipif(os.name=='posix',reason='non-POSIX refusal only')
def test_non_posix_cannot_write_backup_key(tmp_path):
    with pytest.raises(ValueError,match='^MAIL_KEY_BACKUP_REJECTED$'):
        backup.init_backup_key(tmp_path/'secret.json')
    assert list(tmp_path.iterdir())==[]
