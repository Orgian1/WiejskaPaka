import pytest
from scripts import send_verification_batch as cli
from backend import email_verification_mail as mail


def test_no_send_reads_no_settings_keys_or_credentials(monkeypatch):
    monkeypatch.setattr(mail,'load_config',lambda *a:pytest.fail('Secret read'))
    monkeypatch.setattr(cli.worker,'run_process',lambda *a,**kw:pytest.fail('Worker started'))
    assert cli.execute({'WP_ENABLE_VERIFICATION_SMTP':'1'})=={'status':'DISABLED','counts':None}


@pytest.mark.parametrize('env',[
    {}, {'WP_ENABLE_EMAIL_VERIFICATION':'1'},
    {'WP_ENABLE_EMAIL_VERIFICATION':'1','WP_ENABLE_VERIFICATION_SMTP':'1','WP_ENV':'production'},
    {'WP_ENABLE_EMAIL_VERIFICATION':'1','WP_ENABLE_VERIFICATION_SMTP':'1','WP_ENV':'test','WP_MAIL_MIN_INTERVAL_SECONDS':'1','WP_MAIL_DAILY_LIMIT':'100',
     'WP_TEST_DATABASE_URL':'postgresql://private-user:private-secret@localhost/production'}])
def test_bad_configuration_is_private_and_never_starts_worker(monkeypatch,env):
    monkeypatch.setattr(cli.worker,'run_process',lambda *a,**kw:pytest.fail('Worker started'))
    assert cli.execute(env,send=True)=={'status':'WORKER_FAILED','counts':None}


def test_verification_smtp_requires_separate_flag_and_does_not_mutate_environment(monkeypatch):
    from backend import order_mail
    seen=[]
    monkeypatch.setattr(order_mail,'load_ses_config',lambda env:seen.append(env) or 'synthetic-config')
    source={'WP_ENABLE_ORDER_SMTP':'1'}
    assert mail.load_config(source) is None and not seen
    source={'WP_ENABLE_VERIFICATION_SMTP':'1'}
    assert mail.load_config(source)=='synthetic-config'
    assert source=={'WP_ENABLE_VERIFICATION_SMTP':'1'}
    assert seen[0]['WP_ENABLE_ORDER_SMTP']=='1'


def test_dry_command_output_is_fixed(capsys):
    assert cli.main([])==0
    assert capsys.readouterr().out.strip()=='{"counts": null, "status": "DISABLED"}'


def test_unexpected_configuration_errors_are_redacted(monkeypatch):
    from backend import test_server_launcher
    def fail(*a):raise RuntimeError('synthetic-private-password-and-dsn')
    monkeypatch.setattr(test_server_launcher,'prepare_test_server',fail)
    assert cli.execute({'WP_ENABLE_EMAIL_VERIFICATION':'1','WP_ENABLE_VERIFICATION_SMTP':'1'},send=True)=={
        'status':'WORKER_FAILED','counts':None}


def test_valid_configuration_passes_only_bounded_factories(monkeypatch):
    from backend import reset_mail_keys
    from backend.reset_mail_queue import KeyRing
    env={'WP_ENABLE_EMAIL_VERIFICATION':'1','WP_ENABLE_VERIFICATION_SMTP':'1','WP_ENV':'test','WP_MAIL_MIN_INTERVAL_SECONDS':'1','WP_MAIL_DAILY_LIMIT':'100',
         'WP_TEST_DATABASE_URL':'postgresql://test:synthetic-private-password@127.0.0.1/wp_test_mail'}
    keys=KeyRing({'test':b'q'*32},'test')
    monkeypatch.setattr(reset_mail_keys,'load_config',lambda e:keys)
    monkeypatch.setattr(mail,'load_config',lambda e:object())
    def run(connect,actual_keys,transport,**limits):
        assert actual_keys is keys and isinstance(transport,cli.Transport)
        assert connect.database_name=='wp_test_mail'
        assert 'synthetic-private-password' not in repr(connect)
        assert limits.pop('policy').daily_limit==100
        assert limits=={'max_jobs':2,'timeout_seconds':12}
        return {'status':'LIMIT_REACHED','counts':{'ACCEPTED':2}}
    monkeypatch.setattr(cli.worker,'run_process',run)
    assert cli.execute(env,send=True,max_jobs=2,timeout_seconds=12)=={
        'status':'LIMIT_REACHED','counts':{'ACCEPTED':2}}
    env['PGSERVICE']='unexpected-routing'
    assert cli.execute(env,send=True)=={'status':'WORKER_FAILED','counts':None}
