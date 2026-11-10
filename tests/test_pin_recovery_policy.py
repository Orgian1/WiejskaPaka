from datetime import datetime,timedelta,timezone
import sqlite3
import pytest
from backend.pin_recovery import consume_attempt,reply_order_ids,RecoveryError
from backend.checkout_vault import CheckoutStorageError

NOW=datetime(2026,10,16,12,tzinfo=timezone.utc)


@pytest.mark.parametrize('delta,allowed',[(-1,False),(0,True),(1,True)])
def test_fixed_window_boundary(delta,allowed):
    c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row
    c.execute('CREATE TABLE checkout_pin_access(buyer_id INTEGER PRIMARY KEY,attempts INTEGER,window_started_at TEXT)')
    c.execute('INSERT INTO checkout_pin_access VALUES(1,5,?)',((NOW-timedelta(minutes=15,seconds=delta)).isoformat(),))
    if allowed:
        consume_attempt(c,1,NOW);r=c.execute('SELECT * FROM checkout_pin_access').fetchone()
        assert r['attempts']==1 and r['window_started_at']==NOW.isoformat()
    else:
        with pytest.raises(RecoveryError) as caught:consume_attempt(c,1,NOW)
        assert caught.value.status==429 and caught.value.headers['Retry-After']=='1'
    c.close()


def test_backward_clock_cannot_reopen_window():
    c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row
    c.execute('CREATE TABLE checkout_pin_access(buyer_id INTEGER PRIMARY KEY,attempts INTEGER,window_started_at TEXT)')
    c.execute('INSERT INTO checkout_pin_access VALUES(1,1,?)',((NOW+timedelta(seconds=1)).isoformat(),))
    with pytest.raises(RecoveryError) as caught:consume_attempt(c,1,NOW)
    assert caught.value.status==429
    assert c.execute('SELECT attempts FROM checkout_pin_access').fetchone()[0]==1
    c.close()


def test_offset_in_rate_window_is_compared_as_an_instant():
    c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row
    c.execute('CREATE TABLE checkout_pin_access(buyer_id INTEGER PRIMARY KEY,attempts INTEGER,window_started_at TEXT)')
    c.execute('INSERT INTO checkout_pin_access VALUES(1,4,?)',(NOW.astimezone(timezone(timedelta(hours=14))).isoformat(),))
    consume_attempt(c,1,NOW+timedelta(seconds=10))
    assert c.execute('SELECT attempts FROM checkout_pin_access').fetchone()[0]==5
    with pytest.raises(RecoveryError) as caught:consume_attempt(c,1,NOW+timedelta(seconds=10,microseconds=1))
    assert caught.value.headers['Retry-After']=='890'
    c.close()


@pytest.mark.parametrize('response',[{}, {'id':True},{'id':-1},{'id':'1'},
 {'shipment_id':'WPS','orders':[]},{'shipment_id':'WPS','orders':[1]},
 {'shipment_id':'WPS','orders':[{'id':1},{'id':1}]}, {'shipment_id':'WPS','orders':[{}]},
])
def test_mapping_refuses_ambiguous_or_coerced_ids(response):
    with pytest.raises(CheckoutStorageError):reply_order_ids(response)
