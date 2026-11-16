"""Native Windows cmd.exe acceptance; no PowerShell and no private output.

The real source ZIP is extracted into a path containing spaces/Polish letters.
Only processes and temporary directories created by these tests are stopped.
"""
from contextlib import closing
import json
import os
from pathlib import Path
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
import zipfile

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(os.name != 'nt', reason='Native Windows cmd.exe required')


def prepare_venv(folder):
    result = subprocess.run([sys.executable, '-m', 'venv', '--system-site-packages', str(folder)],
                            capture_output=True, timeout=90)
    if result.returncode:
        raise AssertionError('Cannot prepare isolated Windows launcher environment')


def command(script):
    # cmd /s requires the outer quote pair around a quoted batch-file path.
    return '"'+os.environ['COMSPEC']+'" /d /s /c ""'+str(script)+'""'


def stop_tree(process):
    if process.poll() is None:
        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=25)
    process.wait(timeout=25)


def test_actual_cmd_starts_extracted_demo_and_all_roles(tmp_path):
    package = tmp_path/'source.zip'
    result = subprocess.run(['git', 'archive', '--format=zip', '--output='+str(package), 'HEAD'],
                            cwd=ROOT, capture_output=True, timeout=30)
    if result.returncode:
        raise AssertionError('Cannot prepare exact committed source ZIP')
    project = tmp_path/'Wiejska Paka żółć';project.mkdir()
    with zipfile.ZipFile(package) as archive:
        archive.extractall(project)
    script = project/'START_DEMO_WINDOWS.cmd'
    script.write_bytes(script.read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'))
    # First run must exercise the CMD's own venv creation and dependency install.
    runtime = tmp_path/'private-runtime';runtime.mkdir(mode=0o700)
    env = {**os.environ, 'TEMP':str(runtime), 'TMP':str(runtime), 'PYTHONUTF8':'1',
           'PYTHONIOENCODING':'utf-8', 'WP_ENV':'production',
           'DATABASE_URL':'postgresql://127.0.0.1:1/production_must_not_be_opened',
           'NEON_DATABASE_URL':'postgresql://127.0.0.1:1/neon_must_not_be_opened',
           'PAYU_CLIENT_SECRET':'SYNTHETIC-TEST-ONLY', 'WP_ENABLE_ORDER_SMTP':'1',
           'WP_SMTP_HOST':'127.0.0.1', 'WP_SMTP_PORT':'1',
           'WP_TEST_CONTACT_OUTBOX':str(project/'must-not-create')}
    with socket.socket() as probe:
        probe.bind(('127.0.0.1',8765))
    log_path=tmp_path/'private-launcher.log'
    with log_path.open('wb') as log:
        process=subprocess.Popen(command(script),cwd=project,env=env,stdin=subprocess.DEVNULL,
            stdout=log,stderr=log,creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        try:
            with httpx.Client(base_url='http://127.0.0.1:8765',trust_env=False,timeout=5) as client:
                deadline=time.monotonic()+120
                while time.monotonic()<deadline:
                    if process.poll() is not None:
                        raise AssertionError('Windows CMD exited before demo startup; private output withheld')
                    try:
                        reply=client.get('/test/contact/options')
                        if reply.status_code==200 and reply.json()=={'enabled':True,'mode':'local_test'}:
                            break
                    except httpx.TransportError:
                        pass
                    time.sleep(.2)
                else:
                    raise AssertionError('Windows CMD demo startup timed out; private output withheld')
                home=client.get('/')
                if home.status_code!=200:
                    raise AssertionError('Demo home unavailable')
                assets=set(re.findall(r'(?:src|href)="(/assets/[^\"]+)"',home.text))
                if len(assets)<20 or any(client.get(asset).status_code!=200 for asset in assets):
                    raise AssertionError('Packaged frontend assets unavailable')
                text=log_path.read_text(encoding='utf-8',errors='replace')
                accounts={role:(email,password) for role,email,password in re.findall(
                    r'(?m)^(klient|rolnik|dostawca|admin): (\S+) \| hasło: (\S+)\s*$',text)}
                if set(accounts)!={'klient','rolnik','dostawca','admin'}:
                    raise AssertionError('Missing synthetic demo accounts; private output withheld')
                for role,(email,password) in accounts.items():
                    if not email.endswith('@example.invalid'):
                        raise AssertionError('Demo account is not synthetic')
                    logged=client.post('/auth/login',json={'email':email,'password':password})
                    if logged.status_code!=200:
                        raise AssertionError('Synthetic role login failed; private output withheld')
                    headers={'Authorization':'Bearer '+logged.json()['access_token']}
                    identity=client.get('/auth/me',headers=headers)
                    if identity.status_code!=200 or identity.json()['role']!=role:
                        raise AssertionError('Incorrect synthetic account role')
                match=re.search(r'(?m)^Skrzynka testowa odzyskiwania hasła: (.+)$',text)
                if not match:
                    raise AssertionError('Missing private demo directory')
                folder=Path(match.group(1).strip()).parent.resolve()
                if not folder.is_relative_to(runtime.resolve()):
                    raise AssertionError('Demo escaped its private runtime directory')
                database=folder/'sample'/'demo.sqlite3'
                if not database.is_file() or database.read_bytes()[:16]!=b'SQLite format 3\x00':
                    raise AssertionError('Demo did not create its own SQLite database')
                with closing(sqlite3.connect(database.as_uri()+'?mode=ro',uri=True)) as con:
                    if con.execute('SELECT COUNT(*) FROM users').fetchone()[0]!=4:
                        raise AssertionError('Unexpected demo account count')
                if (project/'must-not-create').exists():
                    raise AssertionError('Launcher inherited an external contact directory')
        finally:
            stop_tree(process)
            shutil.rmtree(runtime)


def test_cmd_treats_launcher_cancel_code_130_as_normal_exit(tmp_path):
    project=tmp_path/'Wiejska Paka cancel';project.mkdir()
    shutil.copyfile(ROOT/'START_DEMO_WINDOWS.cmd',project/'START_DEMO_WINDOWS.cmd')
    (project/'requirements-lock.txt').write_text('')
    (project/'scripts').mkdir()
    (project/'scripts'/'run_phone_demo.py').write_text(
        "from pathlib import Path\nPath('cancel-reached.txt').write_text('130')\nraise SystemExit(130)\n")
    prepare_venv(project/'.venv-demo')
    result=subprocess.run(command(project/'START_DEMO_WINDOWS.cmd'),cwd=project,
        stdin=subprocess.DEVNULL,capture_output=True,timeout=120)
    if not (project/'cancel-reached.txt').is_file():
        raise AssertionError('CMD did not invoke the demo entry point')
    if result.returncode!=0:
        raise AssertionError('Normal demo cancellation was reported as a startup failure')
