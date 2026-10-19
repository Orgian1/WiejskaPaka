"""Explicit metadata retention on disposable SQLite; no dispatch or real mail."""
from concurrent.futures import ThreadPoolExecutor
import pytest

from backend import reset_mail_queue as queue, password_reset as reset
from tests.test_reset_mail_queue import store, enqueue, connect, NOW

DAY=86400


def terminal(con, identifier, *, expiry=NOW+900, state='expired'):
    con.execute('''INSERT INTO reset_mail_queue
        (id,user_id,token_hash,event,key_id,payload,created_at,expires_at,state,available_at)
        VALUES(?,1,?,'password_reset','v1',NULL,?,?,?,?)''',
        (identifier,reset.digest(identifier),expiry-900,expiry,state,expiry-900))


@pytest.mark.parametrize('state',['accepted','uncertain','failed','expired'])
def test_only_old_terminal_metadata_is_deleted_at_exact_boundary(store,state):
    con,_,_,_=store
    finished=enqueue(store)
    enqueue(store);enqueue(store)
    with queue.transaction(con):
        con.execute('UPDATE reset_mail_queue SET state=?,payload=NULL WHERE id=?',(state,finished))
        assert queue.claim(con,now=NOW)
    tokens=con.execute('SELECT * FROM password_reset_tokens ORDER BY token_hash').fetchall()
    before=con.execute("SELECT * FROM reset_mail_queue WHERE id!=? ORDER BY id",(finished,)).fetchall()
    with queue.transaction(con):
        assert queue.purge_terminal(con,now=NOW+900+30*DAY-1)=={'deleted':0}
    with queue.transaction(con):
        assert queue.purge_terminal(con,now=NOW+900+30*DAY)=={'deleted':1}
    assert con.execute('SELECT * FROM reset_mail_queue ORDER BY id').fetchall()==before
    assert con.execute('SELECT * FROM password_reset_tokens ORDER BY token_hash').fetchall()==tokens
    assert {r['state'] for r in before}=={'queued','leased'}


def test_batch_order_limit_repeat_and_recent_metadata(store):
    con=store[0]
    with queue.transaction(con):
        for n in range(5):terminal(con,str(n),expiry=NOW+900+n)
        terminal(con,'recent',expiry=NOW+900+10*DAY)
    with queue.transaction(con):
        assert queue.purge_terminal(con,now=NOW+900+DAY+4,retention_seconds=DAY,limit=2)=={'deleted':2}
    assert [r[0] for r in con.execute('SELECT id FROM reset_mail_queue ORDER BY id')]==['2','3','4','recent']
    with queue.transaction(con):
        assert queue.purge_terminal(con,now=NOW+900+DAY+4,retention_seconds=DAY,limit=2)=={'deleted':2}
        assert queue.purge_terminal(con,now=NOW+900+DAY+4,retention_seconds=DAY,limit=2)=={'deleted':1}
        assert queue.purge_terminal(con,now=NOW+900+DAY+4,retention_seconds=DAY,limit=2)=={'deleted':0}
    assert con.execute('SELECT id FROM reset_mail_queue').fetchone()[0]=='recent'


def test_delete_is_rolled_back_with_callers_transaction(store):
    con=store[0]
    with queue.transaction(con):terminal(con,'rollback')
    with pytest.raises(RuntimeError):
        with queue.transaction(con):
            assert queue.purge_terminal(con,now=NOW+900+DAY,retention_seconds=DAY)=={'deleted':1}
            raise RuntimeError('synthetic rollback')
    assert con.execute('SELECT id FROM reset_mail_queue').fetchone()[0]=='rollback'


def test_parallel_maintenance_never_double_counts_deletions(store):
    con,path,_,_=store
    with queue.transaction(con):
        for n in range(8):terminal(con,str(n))
    def run(_):
        other=connect(path)
        try:
            with queue.transaction(other):
                return queue.purge_terminal(other,now=NOW+900+DAY,retention_seconds=DAY,limit=3)['deleted']
        finally:other.close()
    with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(run,range(4)))
    assert sum(results)==8 and all(0<=n<=3 for n in results)
    assert con.execute('SELECT COUNT(*) FROM reset_mail_queue').fetchone()[0]==0


@pytest.mark.parametrize('retention,limit',[(0,1),(86399,1),(366*DAY,1),(True,1),(DAY,0),(DAY,1001),(DAY,True)])
def test_invalid_limits_do_not_delete(store,retention,limit):
    con=store[0]
    with queue.transaction(con):
        terminal(con,'preserve')
        with pytest.raises(ValueError,match='^QUEUE_RETENTION_CONFIGURATION_REJECTED$'):
            queue.purge_terminal(con,now=NOW+400*DAY,retention_seconds=retention,limit=limit)
    assert con.execute('SELECT COUNT(*) FROM reset_mail_queue').fetchone()[0]==1


def test_retention_requires_transaction_and_never_creates_schema(store):
    with pytest.raises(ValueError,match='^QUEUE_REQUIRES_TRANSACTION$'):
        queue.purge_terminal(store[0],now=NOW+DAY)
