"""Synthetic credentials only; configuration validation must stay offline."""
import base64
import json
import os
import socket

import pytest

from scripts import check_mail_configuration as check


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('Local configuration validation attempted network access')
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(socket, 'getaddrinfo', forbidden)


def test_disabled_configuration_does_not_call_loaders(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('Disabled configuration must not read secrets')
    monkeypatch.setattr(check.smtp_reset_transport, 'load_config', forbidden)
    monkeypatch.setattr(check.reset_mail_keys, 'load_config', forbidden)
    assert check.check({}) == {'smtp':'DISABLED', 'queue_keys':'DISABLED',
        'ready_for_connection_test':False, 'network_checked':False, 'delivery_checked':False}


@pytest.mark.skipif(os.name != 'posix', reason='Private secret files require POSIX')
@pytest.mark.parametrize('problem', ['none', 'password-mode', 'keys-mode', 'host', 'keys-format', 'password-missing'])
def test_real_loaders_validate_private_configuration_without_writes(tmp_path, problem, capsys):
    root = tmp_path/'project'
    root.mkdir()
    password = tmp_path/'smtp-password'
    password.write_text('private-synthetic-password\n')
    password.chmod(0o600)
    keys = tmp_path/'mail-keys.json'
    keys.write_text(json.dumps({'format':1, 'active':'v1',
        'keys':{'v1':base64.b64encode(b'a'*32).decode()}}))
    keys.chmod(0o600)
    env = {'WP_ENABLE_SMTP':'1', 'WP_SMTP_HOST':'smtp.example.invalid',
        'WP_SMTP_MODE':'starttls', 'WP_SMTP_PORT':'587', 'WP_SMTP_USERNAME':'private-user',
        'WP_SMTP_FROM':'private-sender@example.invalid', 'WP_PUBLIC_ORIGIN':'https://app.example.invalid',
        'WP_SMTP_PASSWORD_FILE':str(password), 'WP_ENABLE_MAIL_QUEUE':'1',
        'WP_MAIL_QUEUE_KEYS_FILE':str(keys)}
    if problem == 'password-mode': password.chmod(0o644)
    elif problem == 'keys-mode': keys.chmod(0o644)
    elif problem == 'host': env['WP_SMTP_HOST'] = 'private-invalid-host'
    elif problem == 'keys-format': keys.write_text('private-invalid-key-document')
    elif problem == 'password-missing': password.unlink()
    before = {p:p.read_bytes() for p in (password,keys) if p.exists()}
    result = check.check(env, root=root)
    assert result['smtp'] == ('REJECTED' if problem in ('password-mode','host','password-missing') else 'VALID')
    assert result['queue_keys'] == ('REJECTED' if problem in ('keys-mode','keys-format') else 'VALID')
    assert result['ready_for_connection_test'] == (problem == 'none')
    assert result['network_checked'] is result['delivery_checked'] is False
    assert all(p.read_bytes() == raw for p,raw in before.items())
    assert 'private' not in json.dumps(result) and str(tmp_path) not in json.dumps(result)
    assert not capsys.readouterr().out


def test_rejection_of_one_component_does_not_hide_the_other(monkeypatch):
    def rejected(*args, **kwargs): raise ValueError('private-secret-path-and-password')
    monkeypatch.setattr(check.smtp_reset_transport, 'load_config', rejected)
    result = check.check({'WP_ENABLE_SMTP':'1'})
    assert result['smtp'] == 'REJECTED' and result['queue_keys'] == 'DISABLED'
    assert 'private' not in json.dumps(result)


@pytest.mark.parametrize('ready', [False, True])
def test_cli_exit_status_does_not_claim_delivery(monkeypatch, capsys, ready):
    value = {'smtp':'VALID', 'queue_keys':'VALID' if ready else 'DISABLED',
        'ready_for_connection_test':ready, 'network_checked':False, 'delivery_checked':False}
    monkeypatch.setattr(check, 'check', lambda:value)
    assert check.main() == (0 if ready else 1)
    assert json.loads(capsys.readouterr().out) == value
