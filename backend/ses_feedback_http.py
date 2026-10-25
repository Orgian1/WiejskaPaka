"""Explicit standalone SNS notification app factory; never installed at import.

No environment/config/key loading, migration, certificate fetch or subscription
confirmation by default. An explicit callback may handle signed confirmation.
An operator must supply trusted snapshots and a connection factory.
Deploy behind HTTPS with server/proxy resource limits; no launcher is included.
"""
import time
import anyio
from fastapi import FastAPI,Request,Response
from backend.ses_feedback_config import FeedbackConfig
from backend.ses_feedback_archive import ArchiveCipher,receive
from backend.sns_pinned_notification import MAX_BODY,json_object
from backend.reset_mail_queue import transaction
from backend.order_mail_outbox import _postgres


def create_app(config,cipher,connect,*,clock=time.time,max_records=1000,
               retention_seconds=604800,body_timeout=5,max_inflight=8,confirmation=None):
    if (not isinstance(config,FeedbackConfig) or not isinstance(cipher,ArchiveCipher) or
            not callable(connect) or not callable(clock) or type(max_records) is not int or
            not 1<=max_records<=10000 or type(retention_seconds) is not int or
            not 3600<=retention_seconds<=2592000 or type(body_timeout) is not int or
            not 1<=body_timeout<=30 or type(max_inflight) is not int or not 1<=max_inflight<=32 or
            (confirmation is not None and not callable(confirmation))):
        raise ValueError('SES_HTTP_CONFIGURATION_REJECTED')
    app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None)
    capacity=anyio.CapacityLimiter(max_inflight)

    def process(raw):
        con=None
        try:
            if confirmation is not None and json_object(raw).get('Type')=='SubscriptionConfirmation':
                return confirmation(raw,config,now=int(clock())) is True
            con=connect()
            pg=_postgres(con)
            if not pg:con.execute('PRAGMA busy_timeout=2000')
            with transaction(con):
                if pg:
                    con.execute("SET LOCAL statement_timeout = '5000ms'")
                    con.execute("SET LOCAL lock_timeout = '1000ms'")
                receive(con,raw,config,cipher,now=int(clock()),max_records=max_records,
                        retention_seconds=retention_seconds)
            # Only a successful COMMIT permits a successful HTTP response.
            return True
        except Exception:return False
        finally:
            if con is not None:
                try:
                    if _postgres(con):con.connection.close()
                    else:con.close()
                except Exception:pass

    @app.post('/sns/feedback',include_in_schema=False)
    async def notification(request:Request):
        try:capacity.acquire_nowait()
        except anyio.WouldBlock:return Response(status_code=503)
        try:
            if request.headers.get('content-encoding','identity').lower()!='identity':
                return Response(status_code=415)
            length=request.headers.get('content-length')
            if length is not None:
                if not length.isascii() or not length.isdecimal() or len(length)>10:
                    return Response(status_code=400)
                if int(length)>MAX_BODY:return Response(status_code=413)
            chunks=[];size=0
            try:
                with anyio.fail_after(body_timeout):
                    async for chunk in request.stream():
                        size+=len(chunk)
                        if size>MAX_BODY:return Response(status_code=413)
                        if chunk:chunks.append(chunk)
            except TimeoutError:return Response(status_code=408)
            except Exception:return Response(status_code=400)
            if size==0:return Response(status_code=400)
            ok=await anyio.to_thread.run_sync(process,b''.join(chunks))
            return Response(status_code=204 if ok else 503)
        finally:capacity.release()

    return app
