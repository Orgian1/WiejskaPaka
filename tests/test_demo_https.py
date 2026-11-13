"""LAN requires deliberate HTTPS; a real demo starts with a verified local cert."""
from datetime import datetime,timedelta,timezone
import ipaddress
from pathlib import Path
import signal
import socket
import ssl
import subprocess
import sys
import time
from unittest.mock import patch

from cryptography import x509
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
import httpx
import pytest
from scripts.run_phone_demo import demo_listener,main


def certificate_files(folder):
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'WiejskaPaka local test')])
    now=datetime.now(timezone.utc)
    cert=(x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
          .serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(minutes=1))
          .not_valid_after(now+timedelta(days=1))
          .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]),critical=False)
          .sign(key,hashes.SHA256()))
    crt=folder/'demo.pem';private=folder/'demo-key.pem'
    crt.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    private.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
    private.chmod(0o600)
    return crt,private


@pytest.mark.parametrize('host',['0.0.0.0','::','8.8.8.8','169.254.1.2','100.64.0.1','203.0.113.1','224.0.0.1','example.com'])
def test_public_wildcard_and_ambiguous_hosts_are_rejected(host):
    with pytest.raises(ValueError):demo_listener(host)


@pytest.mark.parametrize('host',['192.168.1.5','10.0.0.2','172.16.1.2'])
def test_private_network_without_tls_cannot_start(host):
    with patch('scripts.run_phone_demo.subprocess.call') as server:
        with pytest.raises(SystemExit):main(['--host',host])
        server.assert_not_called()


def test_invalid_or_incomplete_tls_rejected_before_preparation(tmp_path):
    cert,key=certificate_files(tmp_path)
    for args in [(cert,None),(None,key),(cert,cert),(tmp_path/'missing',key)]:
        with pytest.raises(ValueError):demo_listener('127.0.0.1',*args)
    assert demo_listener('127.0.0.1')==('127.0.0.1',[])
    host,options=demo_listener('192.168.1.5',cert,key)
    assert host=='192.168.1.5' and options==['--ssl-certfile',str(cert),'--ssl-keyfile',str(key)]


def test_real_full_demo_uses_verified_https_and_cleans_up(tmp_path):
    cert,key=certificate_files(tmp_path)
    listener=socket.socket();listener.bind(('127.0.0.1',0));port=listener.getsockname()[1];listener.close()
    root=Path(__file__).resolve().parents[1]
    with (tmp_path/'launcher.log').open('w') as log:
        process=subprocess.Popen([sys.executable,'scripts/run_phone_demo.py','--full-demo','--public-geocoder','photon',
            '--port',str(port),'--ssl-certfile',str(cert),'--ssl-keyfile',str(key)],cwd=root,stdout=log,stderr=log,start_new_session=True)
        try:
            tls=ssl.create_default_context(cafile=str(cert))
            with httpx.Client(base_url=f'https://127.0.0.1:{port}',verify=tls,trust_env=False,timeout=3) as client:
                deadline=time.monotonic()+40
                while time.monotonic()<deadline:
                    try:
                        if client.get('/health').status_code==200:break
                    except httpx.HTTPError:pass
                    assert process.poll() is None,'Demo stopped before readiness'
                    time.sleep(.1)
                else:pytest.fail('HTTPS demo not ready')
                assert client.get('/address-search/config').json()=={'enabled':True}
                assert client.get('/assets/leaflet.js').status_code==200
                assert client.get('/').status_code==200
                with pytest.raises(httpx.ConnectError):
                    httpx.get(f'https://127.0.0.1:{port}/health',trust_env=False,timeout=3)
        finally:
            import os
            if os.name=='nt':
                subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,check=False)
                process.wait(timeout=10)
            else:
                os.killpg(process.pid,signal.SIGTERM)
                try:process.wait(timeout=10)
                except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
