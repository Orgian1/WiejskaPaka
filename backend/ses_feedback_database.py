"""Explicit protected local-test PostgreSQL target for standalone SNS ingestion.

No connection on import/load, no schema writes, no production targets. Each new
connection is checked on that same connection before the receiver can use it.
"""
from dataclasses import dataclass,field
import os
from pathlib import Path
import re
import stat
from backend.sns_pinned_notification import json_object

ROOT=Path(__file__).resolve().parents[1]
MAX_BYTES=16384
TABLES=('ses_feedback_events','ses_feedback_review','mail_recipient_blocks')
OPTIONS='-c statement_timeout=5000 -c lock_timeout=1000 -c idle_in_transaction_session_timeout=10000 -c search_path=pg_catalog,public,pg_temp'


def _environment(environ):
    if any(k.startswith('PG') and v for k,v in environ.items()):
        raise ValueError('Inherited libpq settings rejected')


@dataclass(frozen=True)
class Target:
    parameters:tuple=field(repr=False)

    def __call__(self):
        raw=None
        try:
            _environment(os.environ)
            import psycopg
            from psycopg.rows import dict_row
            from backend.pg_adapter import PgConnection
            params=dict(self.parameters)
            raw=psycopg.connect(**params,hostaddr=params['host'],connect_timeout=5,
                                options=OPTIONS,row_factory=dict_row)
            with raw.transaction():
                raw.execute('SET TRANSACTION READ ONLY')
                if raw.execute('SELECT current_database() AS name').fetchone()['name']!=params['dbname']:
                    raise ValueError('Wrong database')
                role=raw.execute('SELECT rolsuper,rolbypassrls,rolcreaterole,rolcreatedb '
                                 'FROM pg_roles WHERE rolname=current_user').fetchone()
                if role is None or any(role.get(k) is not False for k in
                        ('rolsuper','rolbypassrls','rolcreaterole','rolcreatedb')):
                    raise ValueError('Privileged role')
                if raw.execute("SELECT has_schema_privilege(current_user,'public','USAGE') AS allowed").fetchone()['allowed'] is not True:
                    raise ValueError('Schema access required')
                if raw.execute("SELECT current_setting('default_transaction_read_only') AS value").fetchone()['value']!='off':
                    raise ValueError('Writable receiver sessions required')
                rows=raw.execute('SELECT table_name FROM information_schema.tables '
                    "WHERE table_schema='public' AND table_type='BASE TABLE' AND table_name=ANY(%s)",
                    (list(TABLES),)).fetchall()
                if {x['table_name'] for x in rows}!=set(TABLES):raise ValueError('Missing tables')
                for table in TABLES:
                    privileges=['SELECT','INSERT']
                    if table=='mail_recipient_blocks':privileges.append('UPDATE')
                    if table=='ses_feedback_review':privileges.append('DELETE')
                    for privilege in privileges:
                        permitted=raw.execute('SELECT has_table_privilege(current_user,%s,%s) AS allowed',
                                              ('public.'+table,privilege)).fetchone()
                        if permitted is None or permitted['allowed'] is not True:raise ValueError('Missing privilege')
            return PgConnection(raw)
        except Exception:
            if raw is not None:
                try:raw.close()
                except Exception:pass
            raise ValueError('SES_FEEDBACK_DATABASE_REJECTED') from None


def decode(raw):
    try:
        obj=json_object(raw,maximum=MAX_BYTES)
        if (set(obj)!={'format','purpose','connection'} or type(obj['format']) is not int or
                obj['format']!=1 or obj['purpose']!='ses-feedback-database-v1'):
            raise ValueError('Invalid document')
        p=obj['connection']
        if not isinstance(p,dict) or set(p)!={'host','port','database','user','password','sslmode'}:
            raise ValueError('Explicit connection fields required')
        if p['host'] not in ('127.0.0.1','::1') or type(p['port']) is not int or not 1<=p['port']<=65535:
            raise ValueError('Explicit single loopback host required')
        if (not isinstance(p['database'],str) or len(p['database'])>63 or not re.fullmatch(
                r'(?:wp_test_[A-Za-z0-9_]+|wiejskapaka_test(?:_[A-Za-z0-9_]+)?)',p['database'])):
            raise ValueError('Dedicated test database required')
        if (not isinstance(p['user'],str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,62}',p['user']) or
                not isinstance(p['password'],str) or not 1<=len(p['password'])<=1024 or '\x00' in p['password'] or
                p['sslmode'] not in ('disable','require','verify-ca','verify-full')):
            raise ValueError('Explicit credentials and SSL mode required')
        params={'host':p['host'],'port':p['port'],'dbname':p['database'],'user':p['user'],
                'password':p['password'],'sslmode':p['sslmode']}
        return Target(tuple(params.items()))
    except Exception:raise ValueError('SES_FEEDBACK_DATABASE_REJECTED') from None


def load_file(path,*,root=ROOT):
    try:
        path=Path(path)
        if (os.name!='posix' or not path.is_absolute() or path.is_symlink() or
                path.resolve().is_relative_to(Path(root).resolve())):raise ValueError('External private file required')
        fd=os.open(path,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0))
        try:
            info=os.fstat(fd)
            if (not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o077 or
                    info.st_size>MAX_BYTES):raise ValueError('Protected file required')
            raw=os.read(fd,MAX_BYTES+1)
        finally:os.close(fd)
        return decode(raw)
    except Exception:raise ValueError('SES_FEEDBACK_DATABASE_REJECTED') from None


def load_config(environ=None,*,root=ROOT):
    env=dict(os.environ if environ is None else environ)
    if env.get('WP_ENABLE_SES_FEEDBACK_DATABASE')!='1':return None
    try:
        if env.get('WP_ENV') not in ('test','testing'):raise ValueError('Test environment required')
        _environment(env)
        return load_file(env['WP_SES_FEEDBACK_DATABASE_FILE'],root=root)
    except Exception:raise ValueError('SES_FEEDBACK_DATABASE_REJECTED') from None
