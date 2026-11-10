"""Persistent private wallet preview. Never authorizes real orders or bank transfers.

Explicit test/development opt-in only. Balance credits are operator simulations,
not evidence of payment. Replace with signed provider callbacks before production.
"""
import hashlib
import json
import os
import secrets
import time
from argon2 import PasswordHasher
from fastapi import Depends,Header,HTTPException,Query
from pydantic import BaseModel,Field
from backend.order_mail_outbox import _postgres
from backend.invoicing import calculate_commission_grosze

MAX_AMOUNT=100_000_000
MAX_BALANCE=1_000_000_000
LOCK_SECONDS=900
PH=PasswordHasher()
SCHEMA_SQLITE='''
CREATE TABLE IF NOT EXISTS wallet_preview_accounts (
 user_id INTEGER PRIMARY KEY REFERENCES users(id),
 available_grosze INTEGER NOT NULL DEFAULT 0 CHECK(available_grosze BETWEEN 0 AND 1000000000),
 reserved_grosze INTEGER NOT NULL DEFAULT 0 CHECK(reserved_grosze BETWEEN 0 AND 1000000000),
 revision INTEGER NOT NULL DEFAULT 0 CHECK(revision>=0),
 pin_hash TEXT,
 failures INTEGER NOT NULL DEFAULT 0 CHECK(failures BETWEEN 0 AND 5),
 locked_until INTEGER NOT NULL DEFAULT 0,
 CHECK(available_grosze+reserved_grosze<=1000000000)
);
CREATE TABLE IF NOT EXISTS wallet_preview_entries (
 id TEXT PRIMARY KEY,
 user_id INTEGER NOT NULL REFERENCES wallet_preview_accounts(user_id),
 revision INTEGER NOT NULL CHECK(revision>0),
 request_key TEXT NOT NULL,
 payload_hash TEXT NOT NULL,
 kind TEXT NOT NULL CHECK(kind IN ('topup','withdrawal')),
 state TEXT NOT NULL CHECK(state IN ('credited','pending')),
 amount_grosze INTEGER NOT NULL CHECK(amount_grosze BETWEEN 1 AND 100000000),
 available_after INTEGER NOT NULL CHECK(available_after BETWEEN 0 AND 1000000000),
 reserved_after INTEGER NOT NULL CHECK(reserved_after BETWEEN 0 AND 1000000000),
 created_at INTEGER NOT NULL,
 CHECK((kind='topup' AND state='credited') OR (kind='withdrawal' AND state='pending')),
 UNIQUE(user_id,revision),
 UNIQUE(user_id,request_key)
);
'''

from backend import wallet_withdrawals, wallet_intent_recovery
SCHEMA_SQLITE+=wallet_withdrawals.SCHEMA_SQLITE+wallet_intent_recovery.SCHEMA_SQLITE


class AmountIn(BaseModel):
    model_config={'extra':'forbid'}
    amount_grosze:int=Field(strict=True,ge=1,le=MAX_AMOUNT)
    request_key:str=Field(pattern=r'^[A-Za-z0-9_-]{12,100}$')


class RecoveryIn(AmountIn):
    kind:str=Field(pattern=r'^(topup|withdrawal)$')


class WithdrawalIn(AmountIn):
    pin:str=Field(pattern=r'^[0-9]{6}$',repr=False)


class PinIn(BaseModel):
    model_config={'extra':'forbid'}
    password:str=Field(min_length=1,max_length=256,repr=False)
    pin:str=Field(pattern=r'^[0-9]{6}$',repr=False)


def enabled(env=None):
    return (os.environ if env is None else env).get('WP_ENABLE_WALLET_PREVIEW')=='1'


def validate_environment(env):
    if enabled(env) and env.get('WP_ENV') not in ('test','testing','development'):
        raise ValueError('Wallet preview requires private test environment')


def _account(con,user_id):
    con.execute('INSERT INTO wallet_preview_accounts(user_id) VALUES(?) ON CONFLICT(user_id) DO NOTHING',(user_id,))
    suffix=' FOR UPDATE' if _postgres(con) else ''
    return con.execute('SELECT * FROM wallet_preview_accounts WHERE user_id=?'+suffix,(user_id,)).fetchone()


def _pin_matches(encoded,value):
    try:return bool(encoded and PH.verify(encoded,value))
    except Exception:return False


def _failed(con,user_id,account,now):
    count=0 if account['locked_until'] and account['locked_until']<=now else account['failures']
    count=min(5,count+1)
    con.execute('UPDATE wallet_preview_accounts SET failures=?,locked_until=? WHERE user_id=?',
                (count,now+LOCK_SECONDS if count==5 else 0,user_id))


def _locked(account,now):return account['locked_until']>now


def withdrawal_terms(amount_grosze,role):
    """Fixed private-preview quote; reserve gross, fee is included, never added."""
    if role not in ('klient','rolnik'):
        raise ValueError('Unsupported wallet role')
    if type(amount_grosze) is not int or not 1<=amount_grosze<=MAX_AMOUNT:
        raise ValueError('Invalid withdrawal amount')
    rate=500 if role=='rolnik' else 0
    fee=calculate_commission_grosze(amount_grosze,rate)
    return {'gross_grosze':amount_grosze,'fee_grosze':fee,
            'net_grosze':amount_grosze-fee,'fee_basis_points':rate}


def snapshot(con,user_id):
    # One statement keeps balances, frozen terms and terminal states coherent.
    rows=con.execute('''SELECT u.role,a.available_grosze,a.reserved_grosze,a.pin_hash,
        e.id,e.kind,e.state,e.amount_grosze,e.available_after,e.reserved_after,e.created_at,
        t.withdrawal_id,t.gross_grosze,t.fee_basis_points,t.fee_grosze,t.net_grosze,
        r.state AS resolved_state,r.created_at AS resolved_at
        FROM users u LEFT JOIN wallet_preview_accounts a ON a.user_id=u.id
        LEFT JOIN wallet_preview_entries e ON e.user_id=u.id
        LEFT JOIN wallet_preview_terms t ON t.withdrawal_id=e.id
        LEFT JOIN wallet_preview_resolutions r ON r.withdrawal_id=e.id
        WHERE u.id=? ORDER BY e.revision DESC LIMIT 50''',(user_id,)).fetchall()
    row=rows[0]
    history=[]
    for entry in rows:
        if entry['id'] is None:continue
        item={key:entry[key] for key in ('id','kind','state','amount_grosze','available_after','reserved_after','created_at')}
        if item['kind']=='withdrawal':
            if entry['withdrawal_id'] is None:raise HTTPException(409,'Portfel wymaga sprawdzenia.')
            item['withdrawal_preview']={key:entry[key] for key in ('gross_grosze','fee_basis_points','fee_grosze','net_grosze')}
            if entry['resolved_state']:item.update(state=entry['resolved_state'],resolved_at=entry['resolved_at'])
        history.append(item)
    return {'withdrawal_fee_basis_points':500 if row['role']=='rolnik' else 0,
            'available_grosze':row['available_grosze'] or 0,
            'reserved_grosze':row['reserved_grosze'] or 0,
            'pin_configured':bool(row['pin_hash']), 'entries':history}


def move(con,user,payload,kind,*,now):
    account=_account(con,user['id'])
    from backend.wallet_integrity import account_valid
    if not account_valid(con,user['id']):return 409,{'detail':'Portfel wymaga sprawdzenia. Operacja nie została wykonana.'}
    if wallet_intent_recovery.fenced(con,user['id'],payload.request_key):
        return 409,{'detail':'Poprzednie zgłoszenie zostało wycofane. Rozpocznij nową operację.'}
    if kind=='withdrawal':
        if _locked(account,now):return 429,{'detail':'Wypłaty są zablokowane na 15 minut po błędnych próbach PIN-u.'}
        if not account['pin_hash']:return 409,{'detail':'Najpierw ustaw PIN portfela.'}
        if not _pin_matches(account['pin_hash'],payload.pin):
            _failed(con,user['id'],account,now)
            return 403,{'detail':'Nieprawidłowy PIN portfela.'}
        con.execute('UPDATE wallet_preview_accounts SET failures=0,locked_until=0 WHERE user_id=?',(user['id'],))
    fingerprint=hashlib.sha256(json.dumps({'kind':kind,'amount_grosze':payload.amount_grosze},sort_keys=True).encode()).hexdigest()
    previous=con.execute('SELECT id,payload_hash,state FROM wallet_preview_entries WHERE user_id=? AND request_key=?',
                         (user['id'],payload.request_key)).fetchone()
    if previous:
        if previous['payload_hash']!=fingerprint:return 409,{'detail':'Identyfikator operacji został już użyty z inną kwotą lub rodzajem operacji.'}
        resolution=con.execute('SELECT state FROM wallet_preview_resolutions WHERE withdrawal_id=?',(previous['id'],)).fetchone()
        return 200,{'id':previous['id'],'state':resolution['state'] if resolution else previous['state'],**({'withdrawal_preview':wallet_withdrawals.terms(con,previous['id'])} if kind=='withdrawal' else {})}
    available=account['available_grosze'];reserved=account['reserved_grosze']
    if kind=='topup':
        if available+reserved+payload.amount_grosze>MAX_BALANCE:return 409,{'detail':'Przekroczono limit salda portfela.'}
        available+=payload.amount_grosze;state='credited'
    else:
        if payload.amount_grosze>available:return 409,{'detail':'Brak wystarczających dostępnych środków.'}
        available-=payload.amount_grosze;reserved+=payload.amount_grosze;state='pending'
    operation_id=secrets.token_hex(16)
    con.execute('UPDATE wallet_preview_accounts SET available_grosze=?,reserved_grosze=?,revision=revision+1 WHERE user_id=?',(available,reserved,user['id']))
    con.execute('INSERT INTO wallet_preview_entries VALUES(?,?,?,?,?,?,?,?,?,?,?)',
        (operation_id,user['id'],account['revision']+1,payload.request_key,fingerprint,kind,state,payload.amount_grosze,available,reserved,now))
    if kind=='withdrawal':wallet_withdrawals.freeze(con,operation_id,user['role'],withdrawal_terms(payload.amount_grosze,user['role']))
    return 201,{'id':operation_id,'state':state,**({'withdrawal_preview':withdrawal_terms(payload.amount_grosze,user['role'])} if kind=='withdrawal' else {})}


def install(app,db,write_db,current_user,env,database_url):
    validate_environment(env)
    active=enabled(env)
    if active:
        with db() as con:
            if not database_url:
                con.executescript(SCHEMA_SQLITE)
                con.execute(wallet_withdrawals.BACKFILL)
            for table in ('wallet_preview_accounts','wallet_preview_entries','wallet_preview_terms','wallet_preview_resolutions','wallet_preview_operation_fences'):con.execute('SELECT * FROM '+table+' LIMIT 0')
    def allow(user):
        if not active:raise HTTPException(404,'Portfel jest niedostępny.')
        if user['role'] not in ('klient','rolnik'):raise HTTPException(403,'Brak dostępu do portfela.')
    def reply(status,result):
        if status>=400:raise HTTPException(status,result['detail'])
        # Return after transaction commits, including failed PIN counters.
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=status,content=result)
    @app.get('/wallet')
    def read_wallet(user=Depends(current_user)):
        allow(user)
        with db() as con:return snapshot(con,user['id'])
    @app.put('/wallet/pin')
    def set_pin(payload:PinIn,user=Depends(current_user),authorization:str|None=Header(default=None)):
        allow(user);now=int(time.time())
        with write_db(user,authorization,('klient','rolnik')) as con:
            account=_account(con,user['id'])
            if _locked(account,now):status,result=429,{'detail':'Spróbuj ponownie po 15 minutach.'}
            else:
                owner=con.execute('SELECT password_hash FROM users WHERE id=?',(user['id'],)).fetchone()
                if not owner or not _pin_matches(owner['password_hash'],payload.password):
                    _failed(con,user['id'],account,now);status,result=403,{'detail':'Nieprawidłowe hasło konta.'}
                else:
                    con.execute('UPDATE wallet_preview_accounts SET pin_hash=?,failures=0,locked_until=0 WHERE user_id=?',
                                (PH.hash(payload.pin),user['id']))
                    status,result=200,{'pin_configured':True}
        return reply(status,result)
    @app.post('/wallet/topups')
    def topup(payload:AmountIn,user=Depends(current_user),authorization:str|None=Header(default=None)):
        allow(user)
        with write_db(user,authorization,('klient','rolnik')) as con:status,result=move(con,user,payload,'topup',now=int(time.time()))
        return reply(status,result)
    @app.post('/wallet/withdrawals')
    def withdraw(payload:WithdrawalIn,user=Depends(current_user),authorization:str|None=Header(default=None)):
        allow(user)
        with write_db(user,authorization,('klient','rolnik')) as con:status,result=move(con,user,payload,'withdrawal',now=int(time.time()))
        return reply(status,result)

    @app.post('/wallet/withdrawals/{withdrawal_id}/cancel-test')
    def cancel_withdrawal(withdrawal_id:str,user=Depends(current_user),authorization:str|None=Header(default=None)):
        allow(user)
        with write_db(user,authorization,('klient','rolnik')) as con:
            status,result=wallet_withdrawals.resolve(con,user,withdrawal_id,'cancelled_test',now=int(time.time()))
        return reply(status,result)
    @app.get('/admin/wallet/withdrawals-test')
    def pending_withdrawals(limit:int=Query(default=50,ge=1,le=100),offset:int=Query(default=0,ge=0,le=10000),user=Depends(current_user)):
        if not active:raise HTTPException(404,'Portfel jest niedostępny.')
        if user['role']!='admin':raise HTTPException(403,'Brak uprawnień.')
        with db() as con:return wallet_withdrawals.pending(con,limit,offset)
    @app.post('/admin/wallet/withdrawals/{withdrawal_id}/complete-test')
    def complete_withdrawal(withdrawal_id:str,user=Depends(current_user),authorization:str|None=Header(default=None)):
        if not active:raise HTTPException(404,'Portfel jest niedostępny.')
        if user['role']!='admin':raise HTTPException(403,'Brak uprawnień.')
        with write_db(user,authorization,('admin',)) as con:
            status,result=wallet_withdrawals.resolve(con,user,withdrawal_id,'completed_test',now=int(time.time()))
        return reply(status,result)

    @app.post('/wallet/operations/reconcile-test')
    def reconcile_operation(payload:RecoveryIn,user=Depends(current_user),authorization:str|None=Header(default=None)):
        allow(user)
        with write_db(user,authorization,('klient','rolnik')) as con:
            status,result=wallet_intent_recovery.reconcile(con,user,payload,now=int(time.time()))
        return reply(status,result)
