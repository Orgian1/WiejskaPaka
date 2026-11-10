"""Single shared send lease and rolling 24-hour budget per application database.

Claims belong in the SAME transaction as the queue's started marker. No sleeps,
network, environment reads or schema writes occur here. Both SES commands must
use the same persisted policy. Other databases/external senders are out of scope.
"""
from dataclasses import dataclass
import math
import re
import secrets
import time
from backend.order_mail_outbox import _postgres,_require_transaction

SCHEMA_SQLITE='''
CREATE TABLE IF NOT EXISTS mail_send_budget (
 id INTEGER PRIMARY KEY CHECK(id=1),
 min_interval INTEGER NOT NULL CHECK(min_interval BETWEEN 1 AND 3600),
 daily_limit INTEGER NOT NULL CHECK(daily_limit BETWEEN 1 AND 1000000),
 next_allowed INTEGER NOT NULL,
 owner TEXT,
 lease_until INTEGER NOT NULL,
 paused INTEGER NOT NULL CHECK(paused IN (0,1))
 );
CREATE TABLE IF NOT EXISTS mail_send_attempts (
 id TEXT PRIMARY KEY,
 reserved_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS mail_send_attempt_time ON mail_send_attempts(reserved_at);
'''
LEASE_SECONDS=120  # Commands enforce a <=60-second child lifetime plus termination grace.


@dataclass(frozen=True)
class Policy:
    min_interval:int
    daily_limit:int

    def __post_init__(self):
        if (type(self.min_interval) is not int or not 1<=self.min_interval<=3600 or
                type(self.daily_limit) is not int or not 1<=self.daily_limit<=1000000):
            raise ValueError('MAIL_SEND_POLICY_REJECTED')


def load_policy(environ):
    try:
        raw=[environ[k] for k in ('WP_MAIL_MIN_INTERVAL_SECONDS','WP_MAIL_DAILY_LIMIT')]
        if any(not isinstance(x,str) or not re.fullmatch(r'[1-9][0-9]{0,6}',x) for x in raw):
            raise ValueError('Explicit positive limits required')
        return Policy(*map(int,raw))
    except Exception:raise ValueError('MAIL_SEND_POLICY_REJECTED') from None


def _now(value):
    if type(value) is not int or value<0:raise ValueError('MAIL_SEND_TIME_REJECTED')
    return value


def _lock(con):
    _require_transaction(con)
    if _postgres(con):con.execute('SELECT pg_advisory_xact_lock(hashtextextended(?,0))',('wp:mail-send:global',))


class Gate:
    def __init__(self,policy,*,clock=time.time):
        if not isinstance(policy,Policy):raise ValueError('MAIL_SEND_POLICY_REJECTED')
        self.policy=policy;self.clock=clock;self.owner=secrets.token_hex(16)

    def blocked(self,con,email):
        from backend.mail_suppression import blocked
        return blocked(con,email)

    def claim(self,con,now):
        _lock(con);now=_now(now)
        con.execute('''INSERT INTO mail_send_budget
            (id,min_interval,daily_limit,next_allowed,owner,lease_until,paused)
            VALUES(1,?,?,0,NULL,0,0) ON CONFLICT(id) DO NOTHING''',
            (self.policy.min_interval,self.policy.daily_limit))
        row=con.execute('SELECT * FROM mail_send_budget WHERE id=1').fetchone()
        if (row['min_interval'],row['daily_limit'])!=(self.policy.min_interval,self.policy.daily_limit):
            raise ValueError('MAIL_SEND_POLICY_MISMATCH')
        if (row['paused'] or now<row['next_allowed'] or
                (row['owner'] is not None and now<row['lease_until']+self.policy.min_interval)):
            return False
        if row['owner'] is not None:
            # A crashed bounded child may have submitted. Retain its attempt
            # through the full stale lease, never reset the rolling quota.
            con.execute('UPDATE mail_send_attempts SET reserved_at=? WHERE id=? AND reserved_at<?',
                (row['lease_until'],row['owner'],row['lease_until']))
        con.execute('DELETE FROM mail_send_attempts WHERE reserved_at<=?',(now-86400,))
        count=con.execute('SELECT count(*) AS n FROM mail_send_attempts').fetchone()['n']
        if count>=self.policy.daily_limit:return False
        con.execute('INSERT INTO mail_send_attempts VALUES(?,?)',(self.owner,now))
        con.execute('UPDATE mail_send_budget SET owner=?,lease_until=? WHERE id=1',
                    (self.owner,now+LEASE_SECONDS))
        return True

    def finish(self,con):
        _lock(con);now=_now(math.ceil(self.clock()))
        # No decrement on rejection/uncertainty: a submission attempt consumed capacity.
        # max protects pacing when the wall clock moves backwards during SMTP.
        con.execute('UPDATE mail_send_attempts SET reserved_at=? WHERE id=? AND reserved_at<?',
                    (now,self.owner,now))
        con.execute('''UPDATE mail_send_budget SET owner=NULL,lease_until=0,
            next_allowed=CASE WHEN lease_until-? > ? THEN lease_until-?+? ELSE ? END
            WHERE id=1 AND owner=?''',
            (LEASE_SECONDS,now,LEASE_SECONDS,self.policy.min_interval,now+self.policy.min_interval,self.owner))


def quarantine_restored(con):
    _lock(con)
    # No automatic budget reset after restore: the snapshot cannot know how much
    # the original system has sent since it was taken. Require offline review.
    con.execute('''INSERT INTO mail_send_budget
        VALUES(1,1,1,0,NULL,0,1) ON CONFLICT(id) DO UPDATE SET paused=1,owner=NULL,lease_until=0''')
