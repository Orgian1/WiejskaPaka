"""Private read-only check of actual retained REVIEW ciphertext with proposed keys.

No file loading, key rotation, migration, HTTP route, environment or network
connection creation. The operator supplies an existing transaction and a trusted
key snapshot. A successful check is evidence for the inspected rows, not a
promise about backups, other processes, missing historical rows or future writes.
"""
from backend.order_mail_outbox import _require_transaction
from backend.ses_feedback_archive import ArchiveCipher


def check_retained(con,cipher,*,now,max_records=10000):
    """Bound metadata inventory, decrypt one retained record at a time, no writes.

    The caller must coordinate rotation/pause old writers and choose appropriate
    DB read isolation. This does not switch any active process to these keys.
    Retain old key material for backups even after live records have expired.
    """
    try:
        _require_transaction(con)
        if (not isinstance(cipher,ArchiveCipher) or type(now) is not int or now<0 or
                type(max_records) is not int or not 1<=max_records<=10000):
            raise ValueError('Invalid check context')
        # Fetch only bounded small identifiers; never materialize all payloads.
        rows=con.execute('SELECT event_key FROM ses_feedback_review WHERE expires_at>? '
                         'ORDER BY event_key LIMIT ?',(now,max_records+1)).fetchall()
        if len(rows)>max_records:raise ValueError('Inventory exceeds limit')
        for item in rows:
            row=con.execute('SELECT * FROM ses_feedback_review WHERE event_key=? AND expires_at>?',
                            (item['event_key'],now)).fetchone()
            if row is None:raise ValueError('Inventory changed')
            cipher.open(row)
        return {'status':'RETAINED_KEYS_VALID','checked':len(rows)}
    except Exception:raise ValueError('SES_RETAINED_KEYS_REJECTED') from None
