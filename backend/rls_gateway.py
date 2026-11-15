"""Statement capabilities for the restricted PostgreSQL runtime.

The SQL login cannot read/write application tables. A server-held key authorizes
an exact parameter-bound statement on one backend PID, transaction and database.
RLS identity is stored privately by the verifier, never in caller-controlled GUCs.
"""
from contextvars import ContextVar
from contextlib import contextmanager
import hashlib
import hmac
import json
import os
import re
from pathlib import Path
import secrets
import stat
import time

_context = ContextVar('wp_database_request', default=('maintenance', None))


@contextmanager
def database_context(scope, authorization=None):
    if scope not in ('request', 'auth', 'maintenance'):
        raise ValueError('Unknown database scope')
    marker = _context.set((scope, authorization))
    try:
        yield
    finally:
        _context.reset(marker)


class DatabaseContextMiddleware:
    def __init__(self, app):self.app=app
    async def __call__(self, scope, receive, send):
        if scope['type']!='http':return await self.app(scope,receive,send)
        headers=dict(scope.get('headers', []))
        authorization=headers.get(b'authorization',b'').decode('latin1')
        purpose='auth' if scope.get('path','').startswith('/auth/') else 'request'
        with database_context(purpose,authorization):
            await self.app(scope,receive,send)


def load_key():
    path=Path(os.environ.get('WP_RLS_KEY_FILE',''))
    if not os.environ.get('WP_RLS_KEY_FILE') or path.is_symlink():
        raise RuntimeError('RLS signing key configuration required')
    info=path.stat()
    if not stat.S_ISREG(info.st_mode) or (os.name=='posix' and (info.st_uid!=os.getuid() or info.st_mode & 0o077)):
        raise RuntimeError('RLS signing key must be private')
    key=bytes.fromhex(json.loads(path.read_text())['key'])
    if len(key)!=32:raise RuntimeError('Invalid RLS signing key')
    return key


class Result:
    def __init__(self, rows, count):self.rows=iter(rows);self.rowcount=count
    def fetchone(self):return next(self.rows,None)
    def fetchall(self):return list(self.rows)
    def __iter__(self):return self.rows


def execute(connection, sql, params):
    from psycopg import ClientCursor, sql as compose
    from psycopg.pq import Format
    control=sql.strip().upper().rstrip(';')
    safe_timeout=re.fullmatch(r"SET LOCAL (?:STATEMENT_TIMEOUT|LOCK_TIMEOUT)\s*=\s*'[0-9]+(?:MS|S)'",control)
    if safe_timeout or control in ('BEGIN','COMMIT','ROLLBACK','SET TRANSACTION READ ONLY','SET TRANSACTION READ WRITE') or re.fullmatch(r'(?:SAVEPOINT|ROLLBACK TO(?: SAVEPOINT)?|RELEASE(?: SAVEPOINT)?|SHOW) [A-Z_][A-Z_0-9]*',control):
        return connection.execute(sql)
    key=load_key()
    connection.execute("SET LOCAL search_path=pg_catalog,public,pg_temp")
    rendered=ClientCursor(connection).mogrify(sql,params).strip().rstrip(';')
    # PREPARE/DESCRIBE exposes types, not rows, and preserves bytea, NUMERIC,
    # JSON and timestamps through the capability result transport.
    name='wp_desc_'+secrets.token_hex(12)
    connection.execute('SELECT wp_rls.describe(%s,%s)',(rendered,name))
    try:
        description=connection.pgconn.describe_prepared(name.encode())
        if description.error_message:raise RuntimeError('Cannot describe RLS statement')
        columns=[(description.fname(i).decode(),description.ftype(i)) for i in range(description.nfields)]
    finally:
        connection.execute(compose.SQL('DEALLOCATE {}').format(compose.Identifier(name)))
    info=connection.execute('SELECT pg_backend_pid() AS pid, txid_current() AS xid, current_database() AS db').fetchone()
    if not isinstance(info,dict):info=dict(zip(('pid','xid','db'),info))
    purpose,authorization=_context.get()
    bearer=authorization[7:] if isinstance(authorization,str) and authorization.startswith('Bearer ') else None
    payload=json.dumps({**info,'nonce':secrets.token_hex(24),'expires':int(time.time())+60,
        'scope':purpose,'bearer':bearer,'sql':rendered,'columns':columns},ensure_ascii=False,separators=(',',':'))
    mac=hmac.new(key,payload.encode(),hashlib.sha256).hexdigest()
    reply=connection.execute('SELECT wp_rls.execute(%s,%s) AS result',(payload,mac)).fetchone()
    reply=reply['result'] if isinstance(reply,dict) else reply[0]
    rows=[]
    for cells in reply['rows']:
        values=[]
        for cell,(_,oid) in zip(cells,columns):
            if cell is None:values.append(None);continue
            if oid==16:
                values.append(cell in ('t','true'));continue
            loader_cls=connection.adapters.get_loader(oid,Format.TEXT)
            values.append(loader_cls(oid,connection).load(cell.encode()) if loader_cls else cell)
        rows.append(dict(zip((name for name,_ in columns),values)))
    return Result(rows,reply['count'])
