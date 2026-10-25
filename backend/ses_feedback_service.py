"""Compose protected snapshots and read-only startup checks. No automatic server.

prepare() never connects; check() is an explicit DB probe; build_app() validates
before constructing an app, but does not bind/listen or configure AWS/SMTP.
"""
from dataclasses import dataclass,field
import os
import re
import time
from datetime import datetime,timezone
from cryptography import x509
from backend import ses_feedback_config,ses_review_keys,ses_feedback_database
from backend.ses_review_key_check import check_retained
from backend.order_mail_outbox import _postgres


@dataclass(frozen=True)
class Prepared:
    config:object=field(repr=False)
    cipher:object=field(repr=False)
    target:object=field(repr=False)
    max_records:int=1000
    retention_seconds:int=604800
    body_timeout:int=5
    max_inflight:int=8

    def check(self,*,now=None):
        con=None
        try:
            current=int(time.time()) if now is None else now
            if type(current) is not int or current<0:raise ValueError('Invalid clock')
            instant=datetime.fromtimestamp(current,timezone.utc)
            certificates=[x509.load_pem_x509_certificate(pin.certificate_pem) for pin in self.config.pins]
            if not any(cert.not_valid_before_utc<=instant<=cert.not_valid_after_utc for cert in certificates):
                raise ValueError('No currently valid trusted certificate')
            con=self.target()
            if _postgres(con):
                with con.connection.transaction():
                    con.execute('SET TRANSACTION READ ONLY')
                    result=check_retained(con,self.cipher,now=current,max_records=self.max_records)
            else:
                con.execute('BEGIN')
                try:result=check_retained(con,self.cipher,now=current,max_records=self.max_records)
                finally:con.rollback()
            return {'status':'CONFIGURATION_VALID','retained_records':result['checked']}
        except Exception:raise ValueError('SES_FEEDBACK_SERVICE_REJECTED') from None
        finally:
            if con is not None:
                try:
                    if _postgres(con):con.connection.close()
                    else:con.close()
                except Exception:pass

    def build_app(self,*,clock=time.time):
        try:
            self.check(now=int(clock()))
            from backend.ses_feedback_http import create_app
            return create_app(self.config,self.cipher,self.target,clock=clock,
                max_records=self.max_records,retention_seconds=self.retention_seconds,
                body_timeout=self.body_timeout,max_inflight=self.max_inflight)
        except Exception:raise ValueError('SES_FEEDBACK_SERVICE_REJECTED') from None


def _number(env,name,default,minimum,maximum):
    raw=env.get(name,str(default))
    if not isinstance(raw,str) or not re.fullmatch(r'[1-9][0-9]{0,8}',raw):raise ValueError('Invalid policy')
    value=int(raw)
    if not minimum<=value<=maximum:raise ValueError('Invalid policy')
    return value


def prepare(environ=None,*,now=None):
    env=dict(os.environ if environ is None else environ)
    if env.get('WP_ENABLE_SES_FEEDBACK_SERVICE')!='1':return None
    try:
        if (env.get('WP_ENV') not in ('test','testing') or any(env.get(flag)!='1' for flag in
                ('WP_ENABLE_SES_FEEDBACK_CONFIG','WP_ENABLE_SES_REVIEW_KEYS','WP_ENABLE_SES_FEEDBACK_DATABASE'))):
            raise ValueError('Explicit protected test configuration required')
        policy=dict(
            max_records=_number(env,'WP_SES_REVIEW_MAX_RECORDS',1000,1,10000),
            retention_seconds=_number(env,'WP_SES_REVIEW_RETENTION_SECONDS',604800,3600,2592000),
            body_timeout=_number(env,'WP_SES_FEEDBACK_BODY_TIMEOUT',5,1,30),
            max_inflight=_number(env,'WP_SES_FEEDBACK_MAX_INFLIGHT',8,1,32))
        config=ses_feedback_config.load_config(env,now=now)
        cipher=ses_review_keys.load_config(env)
        target=ses_feedback_database.load_config(env)
        if config is None or cipher is None or target is None:raise ValueError('Missing snapshot')
        return Prepared(config,cipher,target,**policy)
    except Exception:raise ValueError('SES_FEEDBACK_SERVICE_REJECTED') from None
