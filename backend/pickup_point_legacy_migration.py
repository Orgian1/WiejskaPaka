"""Dry-run and explicit legacy pickup point entitlement migration.

No implicit wallet debit, free promotion, or backdated activation.
Only an operator-supplied, previously verified paid entitlement may be
imported. The default dry-run makes no writes.
"""
from datetime import datetime, timezone
from uuid import uuid4
from backend.pickup_point_periods import period_end

def import_verified_legacy_period(con, *, point_id, farmer_id, starts_at,
                                  wallet_entry_id, dry_run=True):
    if not wallet_entry_id or not isinstance(wallet_entry_id,str):
        raise ValueError('Verified wallet entry identifier is required')
    if starts_at.tzinfo is None:
        raise ValueError('Timezone-aware payment time is required')
    point=con.execute('SELECT farmer_id FROM pickup_points WHERE id=?',(point_id,)).fetchone()
    if point is None or point['farmer_id']!=farmer_id:
        raise ValueError('Pickup point ownership mismatch')
    existing=con.execute('SELECT id FROM pickup_point_periods WHERE wallet_entry_id=?',
                         (wallet_entry_id,)).fetchone()
    if existing:
        owner=con.execute('SELECT point_id,farmer_id FROM pickup_point_periods WHERE id=?',
                          (existing['id'],)).fetchone()
        if owner['point_id']!=point_id or owner['farmer_id']!=farmer_id:
            raise ValueError('Wallet debit already belongs to another pickup point')
        return {'status':'already_imported','point_id':point_id}
    proposed_start=starts_at.astimezone(timezone.utc)
    proposed_end=period_end(starts_at).astimezone(timezone.utc)
    for period in con.execute('SELECT starts_at,ends_at FROM pickup_point_periods WHERE point_id=?',(point_id,)).fetchall():
        existing_start=datetime.fromisoformat(period['starts_at']).astimezone(timezone.utc)
        existing_end=datetime.fromisoformat(period['ends_at']).astimezone(timezone.utc)
        if proposed_start<existing_end and existing_start<proposed_end:
            raise ValueError('Existing entitlement overlaps imported payment period')
    # A reference is not proof of payment. Verify against a recorded debit.
    entry=con.execute('''SELECT user_id,kind,amount_grosze,state
        FROM wallet_preview_entries WHERE id=?''',(wallet_entry_id,)).fetchone()
    if (entry is None or entry['user_id']!=farmer_id
            or entry['kind']!='point_fee' or entry['state']!='charged'
            or entry['amount_grosze']!=1000):
        raise ValueError('No matching verified 1000-grosz point debit')
    if dry_run:
        return {'status':'dry_run','point_id':point_id,'wallet_entry_id':wallet_entry_id}
    con.execute('''INSERT INTO pickup_point_periods
        (id,point_id,farmer_id,starts_at,ends_at,price_grosze,kind,wallet_entry_id)
        VALUES(?,?,?,?,?,1000,'wallet_test',?)''',
        (str(uuid4()),point_id,farmer_id,starts_at.isoformat(),period_end(starts_at).isoformat(),
         wallet_entry_id))
    return {'status':'imported','point_id':point_id,'wallet_entry_id':wallet_entry_id}
