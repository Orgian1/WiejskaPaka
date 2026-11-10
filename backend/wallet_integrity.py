"""Read-only arithmetic reconciliation of the private wallet journal.

One SELECT gives a coherent statement snapshot. This does not prove that a
provider received a payment, and does not turn preview credits into real funds.
"""
BASE='''WITH history AS (
 SELECT id,user_id,revision,available_after,reserved_after,
 CASE WHEN kind='topup' THEN amount_grosze ELSE -amount_grosze END AS available_delta,
 CASE WHEN kind='withdrawal' THEN amount_grosze ELSE 0 END AS reserved_delta
 FROM wallet_preview_entries
 UNION ALL
 SELECT r.id,r.user_id,r.revision,r.available_after,r.reserved_after,
 CASE WHEN r.state='cancelled_test' THEN t.gross_grosze ELSE 0 END,-t.gross_grosze
 FROM wallet_preview_resolutions r JOIN wallet_preview_terms t ON t.withdrawal_id=r.withdrawal_id
)
SELECT a.user_id,a.available_grosze,a.reserved_grosze,a.revision,
 count(e.id) AS entry_count,min(e.revision) AS first_revision,max(e.revision) AS last_revision,
 coalesce(sum(e.available_delta),0) AS expected_available,
 coalesce(sum(e.reserved_delta),0) AS expected_reserved,
 l.available_after AS latest_available,l.reserved_after AS latest_reserved,
 coalesce(h.invalid_snapshots,0) AS invalid_snapshots,
 coalesce(q.invalid_terms,0) AS invalid_terms
 FROM wallet_preview_accounts a
 LEFT JOIN history e ON e.user_id=a.user_id
 LEFT JOIN history l ON l.user_id=a.user_id AND l.revision=a.revision
 LEFT JOIN (
   SELECT user_id,sum(CASE WHEN available_after<>expected_available OR reserved_after<>expected_reserved THEN 1 ELSE 0 END) AS invalid_snapshots
   FROM (
     SELECT user_id,available_after,reserved_after,
       sum(available_delta) OVER (PARTITION BY user_id ORDER BY revision ROWS UNBOUNDED PRECEDING) AS expected_available,
       sum(reserved_delta) OVER (PARTITION BY user_id ORDER BY revision ROWS UNBOUNDED PRECEDING) AS expected_reserved
     FROM history
   ) snapshots GROUP BY user_id
 ) h ON h.user_id=a.user_id
 LEFT JOIN (
   SELECT e.user_id,sum(CASE
     WHEN e.kind='withdrawal' AND (t.withdrawal_id IS NULL OR t.gross_grosze<>e.amount_grosze
       OR t.fee_grosze<>(t.gross_grosze*t.fee_basis_points+5000)/10000
       OR t.net_grosze+t.fee_grosze<>t.gross_grosze
       OR (r.id IS NOT NULL AND (r.user_id<>e.user_id OR (r.state='cancelled_test' AND r.actor_id<>e.user_id)))) THEN 1
     WHEN e.kind='topup' AND t.withdrawal_id IS NOT NULL THEN 1 ELSE 0 END) AS invalid_terms
   FROM wallet_preview_entries e LEFT JOIN wallet_preview_terms t ON t.withdrawal_id=e.id
   LEFT JOIN wallet_preview_resolutions r ON r.withdrawal_id=e.id GROUP BY e.user_id
 ) q ON q.user_id=a.user_id
'''
GROUP=''' GROUP BY a.user_id,a.available_grosze,a.reserved_grosze,a.revision,
 l.available_after,l.reserved_after,h.invalid_snapshots,q.invalid_terms ORDER BY a.user_id'''



def problems(row):
    issues=[]
    if row['invalid_snapshots']:
        issues.append('JOURNAL_HISTORY_MISMATCH')
    if row['invalid_terms']:
        issues.append('WITHDRAWAL_TERMS_MISMATCH')
    if row['available_grosze']!=row['expected_available']:
        issues.append('AVAILABLE_MISMATCH')
    if row['reserved_grosze']!=row['expected_reserved']:
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
