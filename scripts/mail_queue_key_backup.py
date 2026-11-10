"""Explicit encrypted mail-key backup and restore into a new private POSIX file.

No database, SMTP, environment activation, live-key replacement or worker hooks.
"""
import argparse
import base64
import json
import os
from pathlib import Path
import secrets
import stat
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from backend.reset_mail_keys import load_keys, _decode_keys, MAX_BYTES
from scripts.encrypted_sqlite_snapshot import _publish

MAGIC=b'WPMKEY1\0'
MAX_ARCHIVE=8+1+40+12+MAX_BYTES+16
ERROR='MAIL_KEY_BACKUP_REJECTED'


class _Parser(argparse.ArgumentParser):
    def error(self,message):
        self.exit(2,ERROR+'\n')


def _path(value):
    path=Path(value)
    if (os.name!='posix' or not path.is_absolute() or path.is_symlink()
            or path.resolve().is_relative_to(ROOT)
            or any(parent.is_symlink() for parent in path.parents)):
        raise ValueError('private external path required')
    info=path.parent.stat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o077):
        raise ValueError('private parent required')
    return path


def _document(ring):
    return json.dumps({'format':1,'active':ring.active,'keys':{
        k:base64.b64encode(v).decode('ascii') for k,v in ring._keys.items()}},
        sort_keys=True,separators=(',',':')).encode('utf-8')


def _different(source,wrapper):
    if set(source._keys.values()) & set(wrapper._keys.values()):
        raise ValueError('independent backup keys required')


def _separate(archive,wrapper_path):
    if wrapper_path.resolve().is_relative_to(archive.parent.resolve()):
        raise ValueError('backup key must be outside archive directory')


def _read_archive(path):
    fd=os.open(path,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0))
    try:
        info=os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid()
                or info.st_mode&0o077 or info.st_size>MAX_ARCHIVE):
            raise ValueError('unsafe archive')
        raw=os.read(fd,MAX_ARCHIVE+1)
    finally:os.close(fd)
    if len(raw)>MAX_ARCHIVE:raise ValueError('oversized archive')
    return raw


def init_backup_key(destination):
    try:
        destination=_path(destination)
        raw=json.dumps({'format':1,'active':'backup-v1','keys':{
            'backup-v1':base64.b64encode(secrets.token_bytes(32)).decode('ascii')}}).encode()
        _decode_keys(raw)
        _publish(destination,raw)
        return {'created':True}
    except Exception:
        raise ValueError(ERROR) from None


def backup(source,backup_key,destination):
    try:
        source=_path(source);backup_key=_path(backup_key);destination=_path(destination)
        _separate(destination,backup_key)
        ring=load_keys(source);wrapper=load_keys(backup_key);_different(ring,wrapper)
        kid=wrapper.active.encode('ascii');nonce=secrets.token_bytes(12)
        header=MAGIC+bytes([len(kid)])+kid+nonce
        encrypted=header+AESGCM(wrapper._keys[wrapper.active]).encrypt(nonce,_document(ring),header)
        if (_document(load_keys(source))!=_document(ring) or
                _document(load_keys(backup_key))!=_document(wrapper)):
            raise ValueError('key file changed during backup')
        _publish(destination,encrypted)
        return {'encrypted_backup':True}
    except Exception:
        raise ValueError(ERROR) from None


def restore(archive,backup_key,destination):
    try:
        archive=_path(archive);backup_key=_path(backup_key);destination=_path(destination)
        _separate(archive,backup_key)
        if destination.resolve().is_relative_to(archive.parent.resolve()):
            raise ValueError('restore outside archive directory')
        wrapper=load_keys(backup_key);raw=_read_archive(archive)
        if len(raw)<8+1+1+12+16 or raw[:8]!=MAGIC or not 1<=raw[8]<=40:
            raise ValueError('invalid backup format')
        size=raw[8];header_size=9+size+12
        if len(raw)<header_size+16:raise ValueError('truncated backup')
        kid=raw[9:9+size].decode('ascii');header=raw[:header_size];nonce=header[-12:]
        plaintext=AESGCM(wrapper._keys[kid]).decrypt(nonce,raw[header_size:],header)
        ring=_decode_keys(plaintext);_different(ring,wrapper)
        if _document(load_keys(backup_key))!=_document(wrapper):
            raise ValueError('backup key changed during restore')
        _publish(destination,_document(ring))
        return {'restored':True}
    except Exception:
        raise ValueError(ERROR) from None


def main(argv=None):
    parser=_Parser(description=__doc__)
    commands=parser.add_subparsers(dest='operation',required=True)
    key=commands.add_parser('init-key');key.add_argument('--destination',required=True,type=Path)
    export=commands.add_parser('backup')
    export.add_argument('--source',required=True,type=Path)
    export.add_argument('--backup-key',required=True,type=Path)
    export.add_argument('--destination',required=True,type=Path)
    recover=commands.add_parser('restore')
    recover.add_argument('--archive',required=True,type=Path)
    recover.add_argument('--backup-key',required=True,type=Path)
    recover.add_argument('--destination',required=True,type=Path)
    args=parser.parse_args(argv)
    try:
        if args.operation=='init-key':result=init_backup_key(args.destination)
        elif args.operation=='backup':result=backup(args.source,args.backup_key,args.destination)
        else:result=restore(args.archive,args.backup_key,args.destination)
    except ValueError:
        print(ERROR,file=sys.stderr);return 1
    print(json.dumps(result,sort_keys=True));return 0


if __name__=='__main__':raise SystemExit(main())
