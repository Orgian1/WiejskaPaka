from backend.neon_security_audit import audit_security, SENSITIVE_TABLES


class FakeConnection:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def execute(self, query, params):
        self.calls.append((query, params))
        return self

    def fetchall(self):
        return self.rows


def test_disabled_rls_reported_without_mutation():
    db = FakeConnection([(t, False) for t in SENSITIVE_TABLES])
    result = audit_security(db)
    assert result['checked'] == 5
    assert result['rls_enabled'] == 0
    assert len(result['findings']) == 5
    assert result['ready_for_public_launch'] is False
    assert db.calls[0][1] == ('public', list(SENSITIVE_TABLES))
    assert db.calls[0][0].lstrip().startswith('SELECT')


def test_missing_tables_fail_closed():
    result = audit_security(FakeConnection([('users', True)]))
    assert result['checked'] == 1
    assert len([f for f in result['findings'] if f['issue'] == 'missing_table']) == 4
    assert result['ready_for_public_launch'] is False


def test_enabled_rls_is_not_equivalent_to_proven_authorization():
    result = audit_security(FakeConnection([(t, True) for t in SENSITIVE_TABLES]))
    assert result['rls_enabled'] == 5
    assert result['findings'] == []
    assert result['ready_for_public_launch'] is False
