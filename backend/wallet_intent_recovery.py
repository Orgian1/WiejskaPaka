"""Resolve uncertain private-preview writes without allowing a late duplicate."""
SCHEMA_SQLITE='''
CREATE TABLE IF NOT EXISTS wallet_preview_operation_fences (
 user_id INTEGER NOT NULL REFERENCES wallet_preview_accounts(user_id),
 request_key TEXT NOT NULL,
 kind TEXT NOT NULL CHECK(kind IN ('topup','withdrawal')),
 amount_grosze INTEGER NOT NULL CHECK(amount_grosze BETWEEN 1 AND 100000000),
 created_at INTEGER NOT NULL,
 PRIMARY KEY(user_id,request_key)
);
CREATE TRIGGER IF NOT EXISTS wallet_preview_fences_no_update BEFORE UPDATE ON wallet_preview_operation_fences
 BEGIN SELECT RAISE(ABORT,'immutable operation fence'); END;
CREATE TRIGGER IF NOT EXISTS wallet_preview_fences_no_delete BEFORE DELETE ON wallet_preview_operation_fences
 BEGIN SELECT RAISE(ABORT,'immutable operation fence'); END;
'''


def fenced(con,user_id,key):
    return con.execute('SELECT request_key FROM wallet_preview_operation_fences WHERE user_id=? AND request_key=?',(user_id,key)).fetchone() is not None


def reconcile(con,user,payload,*,now):
    from backend.wallet_preview import _account
    from backend.wallet_integrity import account_valid
    _account(con,user['id'])
    if not account_valid(con,user['id']):
        return 409,{'detail':'Portfel wymaga sprawdzenia. Operacja nie została wykonana.'}
    entry=con.execute('''SELECT e.id,e.kind,e.amount_grosze,e.state,r.state AS resolved_state
        FROM wallet_preview_entries e LEFT JOIN wallet_preview_resolutions r ON r.withdrawal_id=e.id
        WHERE e.user_id=? AND e.request_key=?''',(user['id'],payload.request_key)).fetchone()
    if entry:
        return 200,{'outcome':'committed','id':entry['id'],'kind':entry['kind'],
                    'amount_grosze':entry['amount_grosze'],'state':entry['resolved_state'] or entry['state'],
                    'transfer_executed':False}
    if not fenced(con,user['id'],payload.request_key):
        con.execute('''INSERT INTO wallet_preview_operation_fences(user_id,request_key,kind,amount_grosze,created_at)
            VALUES(?,?,?,?,?)''',(user['id'],payload.request_key,payload.kind,payload.amount_grosze,now))
    return 200,{'outcome':'released','transfer_executed':False}
