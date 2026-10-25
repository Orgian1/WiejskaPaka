"""Transaction-bound SES feedback from a verified pinned SNS notification.

No HTTP endpoint, automatic subscription, certificate download or environment
activation. Topic publishing permissions must separately restrict publication
to the expected SES account/identity. A valid SNS signature alone proves SNS
origin, not which principal was allowed to publish to the topic.
"""
import hashlib
from backend import mail_suppression as blocks
from backend.order_mail_outbox import _require_transaction,_postgres
from backend.sns_pinned_notification import verify,json_object,TOPIC
from backend.smtp_reset_transport import address,hostname

SCHEMA_SQLITE='''
CREATE TABLE IF NOT EXISTS ses_feedback_events (
 event_key TEXT PRIMARY KEY,
 payload_hash TEXT NOT NULL,
 result TEXT NOT NULL CHECK(result IN ('APPLIED','IGNORED','REVIEW')),
 received_at INTEGER NOT NULL
);
'''


def _decision(message,*,source_arn,account):
    obj=json_object(message)
    mail=obj['mail']
    if not isinstance(mail,dict) or mail.get('sourceArn')!=source_arn or mail.get('sendingAccountId')!=account:
        raise ValueError('SES source rejected')
    kind=obj.get('notificationType',obj.get('eventType'))
    if 'notificationType' in obj and 'eventType' in obj and obj['notificationType']!=obj['eventType']:
        raise ValueError('Conflicting event types')
    if kind=='Delivery':return 'IGNORED',None,None
    if kind=='Bounce':
        detail=obj['bounce']
        if detail.get('bounceType')=='Transient':return 'IGNORED',None,None
        if detail.get('bounceType')!='Permanent':return 'REVIEW',None,None
        targets=detail.get('bouncedRecipients');reason='permanent_bounce'
    elif kind=='Complaint':
        detail=obj['complaint']
        if detail.get('complaintFeedbackType')=='not-spam':return 'IGNORED',None,None
        if detail.get('complaintFeedbackType')!='abuse':return 'REVIEW',None,None
        targets=detail.get('complainedRecipients');reason='complaint'
    else:return 'REVIEW',None,None
    destinations=mail.get('destination')
    # Our SMTP path sends to exactly one recipient. Never infer a hidden address
    # or suppress multiple candidate recipients from a redacted complaint.
    if (not isinstance(destinations,list) or len(destinations)!=1 or
            not isinstance(targets,list) or len(targets)!=1 or not isinstance(targets[0],dict) or
            not targets[0].get('emailAddress')):
        return 'REVIEW',None,None
    recipient=address(targets[0]['emailAddress']).lower()
    if recipient!=address(destinations[0]).lower():raise ValueError('Mismatched recipient')
    return 'APPLIED',recipient,reason


def validate_source(topic_arn,source_arn):
    topic=TOPIC.fullmatch(topic_arn)
    if not topic:raise ValueError('Invalid source topic')
    expected='arn:aws:ses:'+topic[1]+':'+topic[2]+':identity/'
    if (not isinstance(source_arn,str) or not source_arn.startswith(expected) or
            not source_arn[len(expected):] or len(source_arn)>512):
        raise ValueError('Invalid source config')
    identity=source_arn[len(expected):]
    if '@' in identity:address(identity)
    elif not hostname(identity):raise ValueError('Invalid source identity')
    return topic[2]


def apply(con,raw,pin,*,source_arn,now):
    """Caller commits/rolls back event deduplication and suppression together.

    Always reverify raw SNS bytes here; never accept a caller's verified flag or
    freely constructed Notification as authority to mutate the registry.
    """
    _require_transaction(con)
    try:
        account=validate_source(pin.topic_arn,source_arn)
        notification=verify(raw,pin,now=now)
        result,recipient,reason=_decision(notification.message,source_arn=source_arn,account=account)
        event_key=hashlib.sha256((notification.topic_arn+'\n'+notification.message_id).encode()).hexdigest()
        payload_hash=hashlib.sha256(notification.message.encode()).hexdigest()
    except Exception:raise ValueError('SES_FEEDBACK_REJECTED') from None
    if _postgres(con):
        con.execute('SELECT pg_advisory_xact_lock(hashtextextended(?,0))',('wp:ses-feedback:'+event_key,))
    row=con.execute('SELECT payload_hash FROM ses_feedback_events WHERE event_key=?',(event_key,)).fetchone()
    if row:
        if row['payload_hash']!=payload_hash:raise ValueError('SES_FEEDBACK_CONFLICT')
        return 'DUPLICATE'
    if recipient is not None:blocks.block(con,recipient,reason,now=now)
    con.execute('INSERT INTO ses_feedback_events VALUES(?,?,?,?)',(event_key,payload_hash,result,now))
    return result
