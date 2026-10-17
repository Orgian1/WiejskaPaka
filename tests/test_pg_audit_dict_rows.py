from backend.neon_rls_preflight import inspect_rls
from backend.neon_security_audit import audit_security


class FakeConnection:
    def __init__(self, rows):
        self.rows = rows
    def execute(self, sql, params):
        self.sql, self.params = sql, params
        return self
    def fetchall(self):
        return self.rows


def test_rls_preflight_accepts_psycopg_dict_rows():
    db = FakeConnection([{'relname': 'orders', 'relrowsecurity': True,
                          'relforcerowsecurity': False, 'policy_count': 2}])
    result = inspect_rls(db)
    assert result['tables']['orders']['status'] == 'manual_review_required'
    assert result['tables']['users']['status'] == 'missing'
    assert not result['ready_for_public_launch']
    assert 'AS policy_count' in db.sql


def test_rls_preflight_rejects_rls_disabled_dict_rows():
    result = inspect_rls(FakeConnection([{'relname': 'users', 'relrowsecurity': False,
                                          'relforcerowsecurity': False, 'policy_count': 0}]))
    assert result['tables']['users']['status'] == 'rls_disabled'


def test_security_audit_accepts_psycopg_dict_rows():
    result = audit_security(FakeConnection([{'tablename': 'orders', 'rowsecurity': False},
                                            {'tablename': 'users', 'rowsecurity': True}]))
    assert result['checked'] == 2
    assert result['rls_enabled'] == 1
    assert any(x['table'] == 'orders' and x['issue'] == 'rls_disabled' for x in result['findings'])
