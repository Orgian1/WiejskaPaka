import json
import os
from contextlib import contextmanager
import pytest
from backend import ses_feedback_database as db
from scripts import check_ses_feedback_database as cli


def document(**changes):
    p={'host':'127.0.0.1','port':5432,'database':'wp_test_receiver','user':'receiver',
       'password':'synthetic-private-secret','sslmode':'disable'}
    p.update(changes)
    return {'format':1,'purpose':'ses-feedback-database-v1','connection':p}


def target(**changes):return db.decode(json.dumps(document(**changes)))


@pytest.mark.parametrize('changes',[
    {'host':'example.invalid'},{'host':'127.0.0.1,example.invalid'},{'host':'localhost'},
    {'port':True},{'port':0},{'database':'wiejskapaka'},{'database':'production'},
    {'database':'wp_test_a;drop'},{'user':'bad;role'},{'password':''},
    {'sslmode':'prefer'},{'options':'-c search_path=evil'},
    {'service':'private'},{'hostaddr':'169.254.169.254'},
])
def test_ambiguous_remote_production_or_inherited_options_rejected(changes):
    with pytest.raises(ValueError,match='^SES_FEEDBACK_DATABASE_REJECTED$'):target(**changes)


@pytest.mark.parametrize('raw',[b'[]',b'{"format":1,"format":1}',b'{"x":NaN}',b'x'*16385],
                         ids=['array','duplicate','constant','oversize'])
def test_strict_bounded_document(raw):
    with pytest.raises(ValueError,match='^SES_FEEDBACK_DATABASE_REJECTED$'):db.decode(raw)


def test_purpose_and_format_are_not_optional():
    for key,value in [('purpose','wrong'),('format',True)]:
        obj=document();obj[key]=value
        with pytest.raises(ValueError,match='^SES_FEEDBACK_DATABASE_REJECTED$'):db.decode(json.dumps(obj))
    assert 'synthetic' not in repr(target()) and 'password' not in repr(target())


class Cursor:
    def __init__(self,row=None,rows=None):self.row=row;self.rows=rows
    def fetchone(self):return self.row
    def fetchall(self):return self.rows


class Connection:
    def __init__(self,problem=None):self.problem=problem;self.closed=False;self.sql=[];self.transactions=0
    @contextmanager
    def transaction(self):
        self.transactions+=1
        yield
        self.transactions-=1
    def close(self):self.closed=True
    def execute(self,sql,params=()):
        assert self.transactions==1
        self.sql.append(sql)
        if self.problem=='query-failure':raise RuntimeError('private-secret-host-password')
        if sql=='SET TRANSACTION READ ONLY':return Cursor()
        if 'current_database' in sql:return Cursor({'name':'wrong' if self.problem=='wrong-db' else 'wp_test_receiver'})
        if 'FROM pg_roles' in sql:
            return Cursor({'rolsuper':self.problem=='superuser','rolbypassrls':False,'rolcreaterole':False,'rolcreatedb':False})
        if 'has_schema_privilege' in sql:return Cursor({'allowed':self.problem!='schema-access'})
        if 'default_transaction_read_only' in sql:return Cursor({'value':'on' if self.problem=='read-only' else 'off'})
        if 'information_schema.tables' in sql:
            return Cursor(rows=[{'table_name':x} for x in db.TABLES if not(self.problem=='missing-table' and x==db.TABLES[0])])
        if 'has_table_privilege' in sql:return Cursor({'allowed':self.problem!='missing-privilege'})
        raise AssertionError('Unexpected SQL')


@pytest.fixture
def fake(monkeypatch):
    for k in list(os.environ):
        if k.startswith('PG'):monkeypatch.delenv(k)
    import psycopg
    calls=[];connection=Connection()
    def connect(**kwargs):calls.append(kwargs);return connection
    monkeypatch.setattr(psycopg,'connect',connect)
    return connection,calls


def test_same_connection_read_only_checks_and_fixed_deadlines(fake):
    raw,calls=fake
    con=target()()
    assert con.connection is raw and not raw.closed and raw.transactions==0
    assert calls[0]['host']==calls[0]['hostaddr']=='127.0.0.1'
    assert calls[0]['connect_timeout']==5 and calls[0]['options']==db.OPTIONS
    assert raw.sql[0]=='SET TRANSACTION READ ONLY'
    assert all(not sql.startswith(('CREATE','INSERT','UPDATE','DELETE')) for sql in raw.sql)


@pytest.mark.parametrize('problem',['wrong-db','superuser','missing-table','missing-privilege','query-failure','schema-access','read-only'])
def test_bad_actual_target_is_closed_and_errors_are_redacted(fake,problem):
    raw,_=fake;raw.problem=problem
    with pytest.raises(ValueError,match='^SES_FEEDBACK_DATABASE_REJECTED$'):target()()
    assert raw.closed


def test_inherited_routing_rechecked_before_every_connection(fake,monkeypatch):
    _,calls=fake;t=target();monkeypatch.setenv('PGHOSTADDR','private-host')
    with pytest.raises(ValueError,match='^SES_FEEDBACK_DATABASE_REJECTED$'):t()
    assert not calls


def test_disabled_means_no_file_or_connection(monkeypatch):
    def forbidden(*args,**kwargs):pytest.fail('Disabled check must not perform work')
    monkeypatch.setattr(db,'load_file',forbidden)
    assert db.load_config({}) is None
    monkeypatch.setattr(cli,'load_config',forbidden)
    assert cli.check({'WP_ENABLE_SES_FEEDBACK_DATABASE':'1'})=={'status':'DISABLED'}


@pytest.mark.skipif(os.name!='posix',reason='POSIX private file boundary')
def test_protected_file_load_does_not_connect_and_probe_closes_connection(tmp_path,fake):
    raw,calls=fake;path=tmp_path/'database.json';path.write_text(json.dumps(document()));path.chmod(0o600)
    env={'WP_ENV':'test','WP_ENABLE_SES_FEEDBACK_DATABASE':'1','WP_SES_FEEDBACK_DATABASE_FILE':str(path)}
    assert isinstance(db.load_config(env),db.Target) and not calls
    assert cli.check(env,connect=True)=={'status':'DATABASE_VALID'} and raw.closed
    path.chmod(0o644)
    assert cli.check(env,connect=True)=={'status':'DATABASE_REJECTED'}


@pytest.mark.skipif(os.name!='posix',reason='POSIX private file boundary')
@pytest.mark.parametrize('problem',['internal','symlink','missing','fifo'])
def test_unsafe_file_locations_fail_closed(tmp_path,problem):
    root=tmp_path/'repo';root.mkdir();path=tmp_path/'db.json'
    path.write_text(json.dumps(document()));path.chmod(0o600)
    if problem=='internal':root=tmp_path
    elif problem=='symlink':
        link=tmp_path/'link';link.symlink_to(path);path=link
    elif problem=='missing':path=tmp_path/'absent-private'
    elif problem=='fifo':path.unlink();os.mkfifo(path,0o600)
    with pytest.raises(ValueError,match='^SES_FEEDBACK_DATABASE_REJECTED$'):db.load_file(path,root=root)
    if problem=='missing':assert not path.exists()


def test_probe_failures_are_redacted(capsys,monkeypatch):
    def broken(*args):raise RuntimeError('private-secret')
    monkeypatch.setattr(cli,'load_config',broken)
    assert cli.main(['--connect'])==1
    assert json.loads(capsys.readouterr().out)=={'status':'DATABASE_REJECTED'}


@pytest.mark.parametrize('override',[{'WP_ENV':'production'},{'WP_ENV':''},{'PGHOSTADDR':'private-host'}])
def test_opt_in_still_requires_test_environment_and_no_inherited_routing(monkeypatch,override):
    def forbidden(*args,**kwargs):pytest.fail('Unsafe environment must fail before reading credentials')
    monkeypatch.setattr(db,'load_file',forbidden)
    env={'WP_ENV':'test','WP_ENABLE_SES_FEEDBACK_DATABASE':'1',
         'WP_SES_FEEDBACK_DATABASE_FILE':'private-path',**override}
    with pytest.raises(ValueError,match='^SES_FEEDBACK_DATABASE_REJECTED$'):db.load_config(env)
