"""Read-only arithmetic reconciliation of the private wallet journal.

One SELECT gives a coherent statement snapshot. This does not prove that a
provider received a payment, and does not turn preview credits into real funds.
"""
BASE='''SELECT a.user_id,a.available_grosze,a.reserved_grosze,a.revision,
 count(e.id) AS entry_count,min(e.revision) AS first_revision,max(e.revision) AS last_revision,
 coalesce(sum(CASE WHEN e.kind='topup' THEN e.amount_grosze ELSE 0 END),0) AS credits,
 coalesce(sum(CASE WHEN e.kind='withdrawal' THEN e.amount_grosze ELSE 0 END),0) AS withdrawals,
 l.available_after AS latest_available,l.reserved_after AS latest_reserved
 FROM wallet_preview_accounts a
 LEFT JOIN wallet_preview_entries e ON e.user_id=a.user_id
 LEFT JOIN wallet_preview_entries l ON l.user_id=a.user_id AND l.revision=a.revision
'''
GROUP=''' GROUP BY a.user_id,a.available_grosze,a.reserved_grosze,a.revision,
 l.available_after,l.reserved_after ORDER BY a.user_id'''


def problems(row):
    issues=[]
    if row['available_grosze']!=row['credits']-row['withdrawals']:
        issues.append('AVAILABLE_MISMATCH')
    if row['reserved_grosze']!=row['withdrawals']:
        issues.append('RESERVED_MISMATCH')
    count=row['entry_count']
    if (row['revision']!=count or (count and (row['first_revision']!=1 or row['last_revision']!=count))):
        issues.append('REVISION_MISMATCH')
    if count and (row['latest_available']!=row['available_grosze'] or row['latest_reserved']!=row['reserved_grosze']):
        issues.append('JOURNAL_TAIL_MISMATCH')
    return issues


def account_valid(con,user_id):
    row=con.execute(BASE+' WHERE a.user_id=?'+GROUP,(user_id,)).fetchone()
    return row is not None and not problems(row)


def inspect_wallets(con,*,maximum=10000):
    if type(maximum) is not int or not 1<=maximum<=100000:raise ValueError('Invalid audit bound')
    rows=con.execute(BASE+GROUP+' LIMIT ?',(maximum+1,)).fetchall()
    if len(rows)>maximum:raise ValueError('Wallet audit capacity exceeded')
    codes=set();invalid=0;entries=0
    for row in rows:
        found=problems(row);invalid+=bool(found);codes.update(found);entries+=row['entry_count']
    return {'success':not invalid,'wallets_checked':len(rows),'entries_checked':int(entries),
            'inconsistent_wallets':invalid,'issue_codes':sorted(codes)}
