"""Opt-in authenticated verification routes. API queues privately; never sends SMTP."""
from datetime import datetime, timezone
from fastapi import Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from backend import email_ownership as proof, email_verification_queue as queue


class ConfirmEmail(BaseModel):
    model_config={'extra':'forbid'}
    token:str=Field(pattern=r'^[A-Za-z0-9_-]{43}$')


def install(app, db, current_user, write_db, environ, database_url):
    keys=None
    if environ.get('WP_ENABLE_EMAIL_VERIFICATION')=='1':
        from backend.reset_mail_keys import load_config
        keys=load_config(environ)
        if keys is None:raise ValueError('EMAIL_VERIFICATION_KEYS_REQUIRED')
        with db() as con:
            if not database_url:con.executescript(queue.SCHEMA_SQLITE)
            for table in ('account_email_proofs','email_verification_limits','email_verification_queue'):
                con.execute('SELECT * FROM '+table+' LIMIT 0')

    def require_enabled():
        if keys is None:raise HTTPException(404,'Potwierdzanie adresu jest niedostępne.')

    @app.get('/auth/email-verification/options')
    def options():return {'enabled':keys is not None}

    @app.get('/auth/email-verification/status')
    def status(user=Depends(current_user)):
        require_enabled()
        with db() as con:return {'verified':proof.verified_recipient(con,user['id'],user['email'])}

    @app.post('/auth/email-verification/request',status_code=202)
    def request_link(request:Request,user=Depends(current_user),authorization:str|None=Header(default=None)):
        require_enabled();now=int(datetime.now(timezone.utc).timestamp())
        with write_db(user,authorization,('klient','rolnik','dostawca','admin')) as con:
            allowed=queue.budget(con,user['id'],request.client.host if request.client else 'unknown','issue',now=now)
            if allowed:queue.enqueue(con,keys,user['id'],now=now)
        if not allowed:raise HTTPException(429,'Zbyt wiele prób. Spróbuj później.',headers={'Retry-After':'3600'})
        return {'message':'Jeśli adres wymaga potwierdzenia, wiadomość została zakolejkowana.'}

    @app.post('/auth/email-verification/confirm')
    def confirm(payload:ConfirmEmail,request:Request,user=Depends(current_user),authorization:str|None=Header(default=None)):
        require_enabled();now=int(datetime.now(timezone.utc).timestamp())
        with write_db(user,authorization,('klient','rolnik','dostawca','admin')) as con:
            allowed=queue.budget(con,user['id'],request.client.host if request.client else 'unknown','consume',now=now)
            verified=allowed and proof.consume(con,user['id'],payload.token,now=now)
            if verified:
                con.execute("UPDATE email_verification_queue SET payload=NULL,state='expired' WHERE user_id=? AND state='queued'",(user['id'],))
        if not allowed:raise HTTPException(429,'Zbyt wiele prób. Spróbuj później.',headers={'Retry-After':'3600'})
        if not verified:raise HTTPException(400,'Link jest nieprawidłowy, wykorzystany lub wygasł.')
        return {'verified':True}
