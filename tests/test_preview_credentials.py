"""Closed-preview credentials must not be exposed or overwrite existing files."""
import json
import os
from pathlib import Path
from unittest.mock import patch
import pytest
from scripts.run_phone_demo import main, private_credentials_file

pytestmark = pytest.mark.skipif(os.name != 'posix', reason='POSIX file permissions')


def test_private_file_is_exclusive_private_and_removed_on_error(tmp_path):
    path = tmp_path/'accounts.json'
    with pytest.raises(RuntimeError):
        with private_credentials_file(path, {'secret': 'synthetic-password'}):
            assert path.stat().st_mode & 0o777 == 0o600
            assert json.loads(path.read_text())['secret'] == 'synthetic-password'
            raise RuntimeError('server stopped')
    assert not path.exists()


@pytest.mark.parametrize('symlink', [False, True])
def test_existing_file_or_symlink_is_never_overwritten(tmp_path, symlink):
    target = tmp_path/'existing';target.write_text('preserve me')
    path = tmp_path/'accounts.json'
    if symlink:path.symlink_to(target)
    else:path.write_text('preserve me')
    with pytest.raises(FileExistsError):
        with private_credentials_file(path, {}):pytest.fail('must not enter')
    assert target.read_text() == 'preserve me'
    assert path.read_text() == 'preserve me'


def test_cleanup_does_not_remove_replacement_file(tmp_path):
    path = tmp_path/'accounts.json'
    with private_credentials_file(path, {}):
        path.rename(tmp_path/'moved')
        path.write_text('replacement')
    assert path.read_text() == 'replacement'


def test_shared_parent_is_rejected(tmp_path):
    parent = tmp_path/'shared';parent.mkdir(mode=0o755)
    with pytest.raises(ValueError):
        with private_credentials_file(parent/'accounts.json', {}):pytest.fail('must not enter')
    assert not (parent/'accounts.json').exists()


def test_launcher_keeps_synthetic_accounts_out_of_console(tmp_path, capsys):
    path = tmp_path/'accounts.json'
    seen = []
    def server(command, **kwargs):
        accounts = json.loads(path.read_text());seen.extend(accounts.values())
        assert set(accounts) == {'klient', 'rolnik', 'dostawca', 'admin'}
        assert command[command.index('--host')+1] == '127.0.0.1'
        assert 'DATABASE_URL' not in kwargs['env']
        return 0
    with patch('scripts.run_phone_demo.subprocess.call', side_effect=server):
        assert main(['--sample-data', '--credentials-file', str(path)]) == 0
    text = capsys.readouterr();output = text.out + text.err
    for account in seen:
        assert account['email'] not in output
        assert account['password'] not in output
    assert not path.exists()


def test_existing_credentials_abort_before_server_start(tmp_path, capsys):
    path = tmp_path/'accounts.json';path.write_text('keep')
    with patch('scripts.run_phone_demo.subprocess.call') as server:
        assert main(['--sample-data', '--credentials-file', str(path)]) == 1
        server.assert_not_called()
    assert path.read_text() == 'keep'
    assert 'demo-admin-' not in capsys.readouterr().out


def test_file_option_requires_sample_data(tmp_path):
    with pytest.raises(SystemExit):main(['--credentials-file',str(tmp_path/'accounts.json')])


def test_real_loopback_preview_login_and_graceful_cleanup(tmp_path):
    import signal
    import socket
    import subprocess
    import sys
    import time
    import httpx
    root = Path(__file__).resolve().parents[1]
    path = tmp_path/'accounts.json'
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0));port = probe.getsockname()[1]
    process = subprocess.Popen([sys.executable, 'scripts/run_phone_demo.py',
        '--sample-data', '--port', str(port), '--credentials-file', str(path)],
        cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        start_new_session=True, text=True)
    try:
        deadline = time.monotonic()+25
        with httpx.Client(base_url=f'http://127.0.0.1:{port}', timeout=0.5, trust_env=False) as client:
            while True:
                assert process.poll() is None, 'Preview exited before readiness'
                try:
                    if client.get('/health').status_code == 200:break
                except httpx.HTTPError:pass
                assert time.monotonic() < deadline, 'Preview startup timeout'
                time.sleep(0.1)
            accounts = json.loads(path.read_text())
            assert client.get('/').status_code == 200
            result = client.post('/auth/login', json=accounts['klient'])
            assert result.status_code == 200
            assert 'access_token' in result.json()
        os.killpg(process.pid, signal.SIGINT)
        output, error = process.communicate(timeout=10)
        assert not path.exists()
        for account in accounts.values():
            assert account['email'] not in output+error
            assert account['password'] not in output+error
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate(timeout=10)
