import os
import pytest
from scripts import send_order_confirmation_batch as cli
from backend import order_mail


def valid_env():return {'WP_ENABLE_ORDER_MAIL_QUEUE':'1','WP_ENABLE_EMAIL_VERIFICATION':'1',
    'WP_ENABLE_ORDER_SMTP':'1','WP_ENV':'test','WP_MAIL_MIN_INTERVAL_SECONDS':'1','WP_MAIL_DAILY_LIMIT':'100',
    'WP_TEST_DATABASE_URL':'postgresql://test:synthetic-private-password@127.0.0.1/wp_test_mail'}


def test_default_command_reads_no_secrets_and_connects_nowhere(monkeypatch,capsys):
    monkeypatch.setattr(cli,'load_vault',lambda *a:pytest.fail('Key read'))
    monkeypatch.setattr(order_mail,'load_ses_config',lambda *a:pytest.fail('SMTP read'))
    monkeypatch.setattr(cli.worker,'run_process',lambda *a,**kw:pytest.fail('Worker started'))
    assert cli.execute(valid_env())=={'status':'DISABLED','counts':None}
    assert cli.main([])==0
    assert capsys.readouterr().out.strip()=='{"counts": null, "status": "DISABLED"}'


@pytest.mark.parametrize('missing',['WP_ENABLE_ORDER_MAIL_QUEUE','WP_ENABLE_EMAIL_VERIFICATION','WP_ENABLE_ORDER_SMTP'])
def test_each_optin_is_required_before_any_secret_read(monkeypatch,missing):
    env=valid_env();env.pop(missing)
    monkeypatch.setattr(cli,'load_vault',lambda *a:pytest.fail('Key read'))
    assert cli.execute(env,send=True)=={'status':'WORKER_FAILED','counts':None}


def test_configuration_and_factories_keep_secrets_private(monkeypatch):
    vault=object();smtp=object()
    monkeypatch.setattr(cli,'load_vault',lambda e:vault)
    monkeypatch.setattr(order_mail,'load_ses_config',lambda e:smtp)
    def run(connect,actual_vault,transport,**limits):
        assert actual_vault is vault and transport.config is smtp
        assert connect.required_tables==('account_email_proofs','order_mail_outbox','mail_send_budget','mail_send_attempts','mail_recipient_blocks')
        assert 'synthetic-private-password' not in repr(connect)
        assert limits.pop('policy').daily_limit==100
        assert limits=={'max_jobs':1,'timeout_seconds':30}
        return {'status':'LIMIT_REACHED','counts':{'ACCEPTED':1}}
    monkeypatch.setattr(cli.worker,'run_process',run)
    assert cli.execute(valid_env(),send=True)=={'status':'LIMIT_REACHED','counts':{'ACCEPTED':1}}
    env=valid_env();env['PGSERVICE']='unexpected'
    assert cli.execute(env,send=True)=={'status':'WORKER_FAILED','counts':None}


def test_key_loader_reads_only_existing_protected_external_ring(tmp_path):
    if os.name!='posix':pytest.skip('Private POSIX checkout key')
    from backend.checkout_vault import create_ring
    path=tmp_path/'checkout-key.json';create_ring(path)
    vault=cli.load_vault({'WP_CHECKOUT_KEY_FILE':str(path)},root=tmp_path/'repository')
    assert len(vault.keys)==1
    path.chmod(0o644)
    with pytest.raises(ValueError,match='ORDER_WORKER_VAULT_REJECTED'):
        cli.load_vault({'WP_CHECKOUT_KEY_FILE':str(path)})
    absent=tmp_path/'absent.json'
    with pytest.raises(ValueError,match='ORDER_WORKER_VAULT_REJECTED'):
        cli.load_vault({'WP_CHECKOUT_KEY_FILE':str(absent)})
    assert not absent.exists()


def test_vault_inside_repository_and_symlinks_are_rejected(tmp_path):
    if os.name!='posix':pytest.skip('Private POSIX checkout key')
    from backend.checkout_vault import create_ring
    path=tmp_path/'checkout-key.json';create_ring(path)
    with pytest.raises(ValueError,match='ORDER_WORKER_VAULT_REJECTED'):
        cli.load_vault({'WP_CHECKOUT_KEY_FILE':str(path)},root=tmp_path)
    link=tmp_path/'link.json';link.symlink_to(path)
    with pytest.raises(ValueError,match='ORDER_WORKER_VAULT_REJECTED'):
        cli.load_vault({'WP_CHECKOUT_KEY_FILE':str(link)})


def test_exceptions_are_redacted_and_uncertain_results_exit_nonzero(monkeypatch,capsys):
    def fail(*args,**kwargs):raise RuntimeError('synthetic-private-password-and-pin')
    monkeypatch.setattr(cli,'load_vault',fail)
    assert cli.execute(valid_env(),send=True)=={'status':'WORKER_FAILED','counts':None}
    monkeypatch.setattr(cli,'execute',lambda *a,**kw:{'status':'LIMIT_REACHED','counts':{'DELIVERY_UNCERTAIN':1}})
    assert cli.main(['--send'])==1
    assert 'synthetic-private' not in capsys.readouterr().out
