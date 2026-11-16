import sqlite3

import pytest

from backend.payu_journal_schema import initialize_test_journal


def test_provider_journal_schema_rejects_duplicate_events_and_bad_money():
    con = sqlite3.connect(":memory:")
    try:
        initialize_test_journal(con)
        con.execute("""INSERT INTO provider_payment_operations
            (operation_id,user_id,provider,amount_grosze,status)
            VALUES ('op-1',1,'simulated',100,'PENDING')""")
        con.execute("""INSERT INTO provider_payment_events
            (event_id,operation_id,event_type,verified)
            VALUES ('event-1','op-1','paid',1)""")
        with pytest.raises(sqlite3.IntegrityError):
            con.execute("""INSERT INTO provider_payment_events
                (event_id,operation_id,event_type) VALUES ('event-1','op-1','paid')""")
        with pytest.raises(sqlite3.IntegrityError):
            con.execute("""INSERT INTO provider_payment_operations
                (operation_id,user_id,provider,amount_grosze,status)
                VALUES ('op-2',1,'simulated',-1,'PENDING')""")
        with pytest.raises(sqlite3.IntegrityError):
            con.execute("""INSERT INTO provider_payout_requests
                (payout_id,user_id,role,gross_grosze,net_grosze,fee_grosze,status)
                VALUES ('p-1',1,'rolnik',100,90,5,'REQUESTED')""")
        con.execute("""INSERT INTO provider_payout_requests
            (payout_id,user_id,role,gross_grosze,net_grosze,fee_grosze,status)
            VALUES ('p-2',1,'rolnik',100,95,5,'REQUESTED')""")
    finally:
        con.close()
