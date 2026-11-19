"""Preview existing pickup points before any entitlement backfill.

Read-only by design: never grants a free period, changes point visibility,
or claims a wallet payment. Run migration only after explicit policy approval.
"""
from datetime import datetime, timezone
from backend.pickup_point_periods import active_period, now_warsaw

def inspect_legacy_points(con, *, now=None):
    now=now or now_warsaw()
    points=con.execute('''SELECT id,farmer_id,name,active
        FROM pickup_points ORDER BY id''').fetchall()
    result={'total':len(points),'active_with_entitlement':0,
            'active_without_entitlement':0,'inactive':0,'items':[]}
    for row in points:
        period=active_period(con,row['id'],now=now)
        if not row['active']:
            state='inactive'
        elif period:
            state='active_with_entitlement'
        else:
            state='active_without_entitlement'
        result[state]+=1
        result['items'].append({'point_id':row['id'],'farmer_id':row['farmer_id'],
                                'name':row['name'],'state':state,
                                'expires_at':period['ends_at'] if period else None})
    return result
