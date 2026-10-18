"""Launcher wiring and failures must not start an empty or untrusted sample."""
import json
from pathlib import Path
import sqlite3
import subprocess
from unittest.mock import patch
import pytest
from scripts.run_phone_demo import main


def test_sample_flag_prepares_new_database_and_cleans_it_after_server_exit(capsys):
    seen=[]
    def server(command,**kwargs):
        env=kwargs['env'];database=Path(env['WIEJSKAPAKA_DB']);seen.append(database)
        assert database.is_file() and database.parent.name=='sample'
        assert env['WP_ENABLE_TEST_PAYMENTS']=='1'
        assert env['WP_ENABLE_TEST_PASSWORD_RESET']=='1'
        assert command[command.index('--host')+1]=='127.0.0.1'
        with sqlite3.connect(database) as con:
            assert con.execute('SELECT COUNT(*) FROM users').fetchone()[0]==4
        return 0
    with patch('scripts.run_phone_demo.subprocess.call',side_effect=server):
        assert main(['--sample-data','--port','8767'])==0
    assert not seen[0].parent.exists()
    output=capsys.readouterr()
    assert 'Jednorazowe konta demo' in output.out
    assert all(role+': demo-' in output.out for role in ('klient','rolnik','dostawca','admin'))


@pytest.mark.parametrize('problem',['failure','timeout','bad_json','bad_database','missing_accounts'])
def test_failed_preparation_never_starts_server_or_prints_private_child_output(capsys,problem):
    def prepare(command,**kwargs):
        if problem=='timeout':raise subprocess.TimeoutExpired(command,120,output='private-child-output')
        output='private-child-output'
        code=1 if problem=='failure' else 0
        if problem=='bad_database':output=json.dumps({'database':'foreign.sqlite3','credentials':{}})
        if problem=='missing_accounts':output=json.dumps({'database':str(Path(command[-1])/'demo.sqlite3'),'credentials':{}})
        return subprocess.CompletedProcess(command,code,output,'private-child-error')
    with patch('scripts.run_phone_demo.subprocess.run',side_effect=prepare),patch('scripts.run_phone_demo.subprocess.call') as server:
        assert main(['--sample-data'])==1
        server.assert_not_called()
    output=capsys.readouterr()
    assert 'private-child' not in output.out+output.err
    assert 'foreign.sqlite3' not in output.out+output.err
