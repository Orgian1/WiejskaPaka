"""Terminal states for private wallet simulations; never calls a bank or PSP."""
import secrets

SCHEMA_SQLITE='''
CREATE TABLE IF NOT EXISTS wallet_preview_terms (
 withdrawal_id TEXT PRIMARY KEY REFERENCES wallet_preview_entries(id),
 owner_role TEXT NOT NULL CHECK(owner_role IN ('klient','rolnik')),
 gross_grosze INTEGER NOT NULL CHECK(gross_grosze BETWEEN 1 AND 100000000),
 fee_basis_points INTEGER NOT NULL CHECK(fee_basis_points IN (0,500)),
 fee_grosze INTEGER NOT NULL CHECK(fee_grosze>=0),
 net_grosze INTEGER NOT NULL CHECK(net_grosze>=0),
 CHECK((owner_role='rolnik' AND fee_basis_points=500) OR (owner_role='klient' AND fee_basis_points=0)),
 CHECK(fee_grosze=(gross_grosze*fee_basis_points+5000)/10000),
 CHECK(net_grosze+fee_grosze=gross_grosze)
);
CREATE TABLE IF NOT EXISTS wallet_preview_resolutions (
 id TEXT PRIMARY KEY,
 withdrawal_id TEXT NOT NULL UNIQUE REFERENCES wallet_preview_terms(withdrawal_id),
 user_id INTEGER NOT NULL REFERENCES wallet_preview_accounts(user_id),
 actor_id INTEGER NOT NULL REFERENCES users(id),
 revision INTEGER NOT NULL CHECK(revision>0),
 state TEXT NOT NULL CHECK(state IN ('completed_test','cancelled_test')),
 available_after INTEGER NOT NULL CHECK(available_after BETWEEN 0 AND 1000000000),
 reserved_after INTEGER NOT NULL CHECK(reserved_after BETWEEN 0 AND 1000000000),
 created_at INTEGER NOT NULL,
 UNIQUE(user_id,revision)
);
CREATE INDEX IF NOT EXISTS wallet_preview_resolutions_user_idx ON wallet_preview_resolutions(user_id);
CREATE TRIGGER IF NOT EXISTS wallet_preview_terms_no_update BEFORE UPDATE ON wallet_preview_terms
 BEGIN SELECT RAISE(ABORT,'immutable withdrawal terms'); END;
CREATE TRIGGER IF NOT EXISTS wallet_preview_terms_no_delete BEFORE DELETE ON wallet_preview_terms
 BEGIN SELECT RAISE(ABORT,'immutable withdrawal terms'); END;
CREATE TRIGGER IF NOT EXISTS wallet_preview_resolutions_no_update BEFORE UPDATE ON wallet_preview_resolutions
 BEGIN SELECT RAISE(ABORT,'immutable withdrawal resolution'); END;
CREATE TRIGGER IF NOT EXISTS wallet_preview_resolutions_no_delete BEFORE DELETE ON wallet_preview_resolutions
 BEGIN SELECT RAISE(ABORT,'immutable withdrawal resolution'); END;
'''

BACKFILL='''INSERT INTO wallet_preview_terms
 (withdrawal_id,owner_role,gross_grosze,fee_basis_points,fee_grosze,net_grosze)
 SELECT e.id,u.role,e.amount_grosze,
 CASE WHEN u.role='rolnik' THEN 500 ELSE 0 END,
 CASE WHEN u.role='rolnik' THEN (e.amount_grosze*500+5000)/10000 ELSE 0 END,
 e.amount_grosze-CASE WHEN u.role='rolnik' THEN (e.amount_grosze*500+5000)/10000 ELSE 0 END
 FROM wallet_preview_entries e JOIN users u ON u.id=e.user_id
 WHERE e.kind='withdrawal' AND u.role IN ('klient','rolnik')
 AND NOT EXISTS(SELECT 1 FROM wallet_preview_terms t WHERE t.withdrawal_id=e.id)'''


def freeze(con,withdrawal_id,role,terms):
    con.execute('''INSERT INTO wallet_preview_terms
        (withdrawal_id,owner_role,gross_grosze,fee_basis_points,fee_grosze,net_grosze)
        VALUES(?,?,?,?,?,?)''',
        (withdrawal_id,role,terms['gross_grosze'],terms['fee_basis_points'],terms['fee_grosze'],terms['net_grosze']))


def terms(con,withdrawal_id):
    row=con.execute('SELECT gross_grosze,fee_basis_points,fee_grosze,net_grosze FROM wallet_preview_terms WHERE withdrawal_id=?',(withdrawal_id,)).fetchone()
    if row is None:raise ValueError('Missing immutable withdrawal terms')
    return dict(row)


def resolve(con,actor,withdrawal_id,state,*,now):
    from backend.wallet_preview import _account
    from backend.wallet_integrity import account_valid
    entry=con.execute("SELECT user_id,amount_grosze FROM wallet_preview_entries WHERE id=? AND kind='withdrawal'",(withdrawal_id,)).fetchone()
    if entry is None or (state=='cancelled_test' and entry['user_id']!=actor['id']):
        return 404,{'detail':'Nie znaleziono wniosku wypłaty.'}
    if state not in ('completed_test','cancelled_test') or (state=='completed_test' and actor['role']!='admin') or (state=='cancelled_test' and actor['role'] not in ('klient','rolnik')):
        return 403,{'detail':'Brak uprawnień.'}
    account=_account(con,entry['user_id'])
    if not account_valid(con,entry['user_id']):
        return 409,{'detail':'Portfel wymaga sprawdzenia. Operacja nie została wykonana.'}
    previous=con.execute('SELECT state FROM wallet_preview_resolutions WHERE withdrawal_id=?',(withdrawal_id,)).fetchone()
    if previous:
        if previous['state']!=state:return 409,{'detail':'Wniosek ma już inny stan końcowy. Odśwież portfel.'}
        return 200,{'id':withdrawal_id,'state':state,'transfer_executed':False}
    amount=entry['amount_grosze']
    available=account['available_grosze']+(amount if state=='cancelled_test' else 0)
    reserved=account['reserved_grosze']-amount
    con.execute('UPDATE wallet_preview_accounts SET available_grosze=?,reserved_grosze=?,revision=revision+1 WHERE user_id=?',
                (available,reserved,entry['user_id']))
    con.execute('''INSERT INTO wallet_preview_resolutions
        (id,withdrawal_id,user_id,actor_id,revision,state,available_after,reserved_after,created_at)
        VALUES(?,?,?,?,?,?,?,?,?)''',
        (secrets.token_hex(16),withdrawal_id,entry['user_id'],actor['id'],account['revision']+1,state,available,reserved,now))
    return 201,{'id':withdrawal_id,'state':state,'transfer_executed':False}


def pending(con,limit,offset):
    rows=con.execute('''SELECT e.id,e.user_id,e.created_at,t.owner_role,t.gross_grosze,t.fee_basis_points,t.fee_grosze,t.net_grosze
        FROM wallet_preview_entries e JOIN wallet_preview_terms t ON t.withdrawal_id=e.id
        LEFT JOIN wallet_preview_resolutions r ON r.withdrawal_id=e.id
        WHERE e.kind='withdrawal' AND r.id IS NULL ORDER BY e.created_at,e.id LIMIT ? OFFSET ?''',(limit,offset)).fetchall()
    return {'items':[dict(row) for row in rows],'limit':limit,'offset':offset,'transfer_executed':False}
