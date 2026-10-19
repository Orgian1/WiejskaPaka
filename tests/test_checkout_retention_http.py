"""Periodic checkout PIN retention through actual HTTP, with its own module budget."""
from contextlib import closing
from datetime import datetime,timedelta,timezone
import json
import sqlite3
import pytest
from backend.checkout_vault import read_ring,Vault
from tests.test_purchase_record_http_restart import server,setup
from tests.test_checkout_vault_http import create


def test_running_server_purges_expired_secret_without_restart(tmp_path):
    import time
    database=tmp_path/'worker.sqlite3';keyfile=tmp_path/'worker.sqlite3.checkout-key'
    with server(database) as client:
        farmer,buyer,products=setup(client);key,body,url,headers,result=create(client,buyer,products[0])
        v=Vault(*read_ring(keyfile))
        with closing(sqlite3.connect(database)) as con, con:
            con.row_factory=sqlite3.Row;row=con.execute('SELECT * FROM checkout_idempotency').fetchone()
            sealed=v.seal(result,row['buyer_id'],row['request_key'],row['payload_hash'],
                         pin_until=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat())
            con.execute('UPDATE checkout_idempotency SET response_json=?',(sealed,))
        # Read protection works immediately, even before the periodic rewrite.
        response=client.post(url,headers=headers,json=body)
        assert response.status_code==201 and response.json()['pin_available'] is False
        end=time.monotonic()+36
        while time.monotonic()<end:
            with closing(sqlite3.connect(database)) as con, con:
                raw=con.execute('SELECT response_json FROM checkout_idempotency').fetchone()[0]
            if json.loads(raw)['pin_state']=='redacted':break
            time.sleep(.2)
        else:pytest.fail('Automatic checkout retention worker did not purge PIN within 36 seconds')
        assert 'pin_test_only' not in v._decrypt(raw,row['buyer_id'],row['request_key'],row['payload_hash'])[0]
