"""Explicit private test mode and inherited-environment isolation."""
import pytest
from backend import reset_mail_flow as flow
from backend.reset_mail_queue import KeyRing
from scripts.run_phone_demo import demo_environment
from scripts.run_tests_isolated import test_environment as isolated_env


def base():return {'WP_ENV':'test','WP_ENABLE_TEST_RESET_QUEUE':'1','WP_ENABLE_MAIL_QUEUE':'1'}


def test_default_never_loads_a_key(monkeypatch):
    monkeypatch.setattr(flow,'load_config',lambda *a:pytest.fail('No key read while disabled'))
    assert flow.load_test_queue_keys({},'',reset_enabled=False) is None


@pytest.mark.parametrize('patch,enabled',[
 ({},False),({'WP_ENV':'development'},True),({'WP_ENV':'production'},True),
 ({'WP_TEST_RESET_OUTBOX':'private-filebox'},True),({'WP_ENV':'unknown'},True)])
def test_invalid_modes_are_rejected_before_key_read(monkeypatch,patch,enabled):
    env=base();env.update(patch)
    monkeypatch.setattr(flow,'load_config',lambda *a:pytest.fail('invalid mode cannot read keys'))
    with pytest.raises(ValueError,match='^TEST_RESET_QUEUE_CONFIGURATION_REJECTED$'):
        flow.load_test_queue_keys(env,'',reset_enabled=enabled)


def test_missing_opt_in_and_private_loader_error_are_redacted(monkeypatch):
    monkeypatch.setattr(flow,'load_config',lambda *a:None)
    with pytest.raises(ValueError,match='^TEST_RESET_QUEUE_CONFIGURATION_REJECTED$'):
        flow.load_test_queue_keys(base(),'',reset_enabled=True)
    def bad(*args):raise ValueError('private-path-and-secret')
    monkeypatch.setattr(flow,'load_config',bad)
    with pytest.raises(ValueError,match='^TEST_RESET_QUEUE_CONFIGURATION_REJECTED$') as caught:
        flow.load_test_queue_keys(base(),'',reset_enabled=True)
    assert caught.value.__cause__ is None


def test_explicit_sqlite_configuration_returns_loaded_keys(monkeypatch):
    keys=KeyRing({'v1':b'a'*32},'v1');monkeypatch.setattr(flow,'load_config',lambda *a:keys)
    assert flow.load_test_queue_keys(base(),'',reset_enabled=True) is keys


def test_postgres_requires_a_separate_local_target_opt_in_before_key_read(monkeypatch):
    monkeypatch.setattr(flow,'load_config',lambda *a:pytest.fail('remote or missing PG opt-in cannot read keys'))
    for dsn in ('host=localhost dbname=wp_test_queue','host=outside.invalid dbname=wp_test_queue password=private-secret'):
        with pytest.raises(ValueError,match='^TEST_RESET_QUEUE_CONFIGURATION_REJECTED$'):
            flow.load_test_queue_keys(base(),dsn,reset_enabled=True)


@pytest.mark.parametrize('builder',[demo_environment,isolated_env])
def test_test_launchers_strip_all_queue_enablement_and_private_key_paths(builder,tmp_path):
    env=builder({'WP_ENABLE_TEST_RESET_QUEUE':'1','WP_ENABLE_MAIL_QUEUE':'1',
                 'WP_MAIL_QUEUE_KEYS_FILE':'private-secret-path'},tmp_path/'demo.sqlite3')
    assert not {'WP_ENABLE_TEST_RESET_QUEUE','WP_ENABLE_MAIL_QUEUE','WP_MAIL_QUEUE_KEYS_FILE'}&env.keys()
