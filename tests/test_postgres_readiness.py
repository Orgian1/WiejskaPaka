from backend.postgres_readiness import inspect_postgres, SENSITIVE_TABLES


class FakeCursor:
    def __init__(self, row):
        self.row = row

    def fetchone(self):
        return self.row


class FakeConnection:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def execute(self, sql, params):
        self.calls.append((sql, params))
        return FakeCursor(self.rows.get(params[0]))


def test_missing_tables_are_flagged_and_queries_parameterized():
    db = FakeConnection({})
    result = inspect_postgres(db)
    assert result['missing_tables'] == list(SENSITIVE_TABLES)
    assert result['requires_review'] is True
    assert len(db.calls) == len(SENSITIVE_TABLES)
    assert all(args == (args[0], args[0]) for _, args in db.calls)
    assert all('?' in sql for sql, _ in db.calls)


def test_rls_disabled_and_policy_count_reported_without_false_certification():
    rows = {t: {'rls_enabled': True, 'rls_forced': False, 'policy_count': 2, 'can_select': True}
            for t in SENSITIVE_TABLES}
    rows['orders'] = {**rows['orders'], 'rls_enabled': False}
    result = inspect_postgres(FakeConnection(rows))
    assert result['rls_disabled'] == ['orders']
    assert result['missing_tables'] == []
    assert result['rls_is_not_verified'] is True


def test_even_enabled_rls_does_not_claim_readiness():
    rows = {t: {'rls_enabled': True, 'rls_forced': True, 'policy_count': 1, 'can_select': True}
            for t in SENSITIVE_TABLES}
    result = inspect_postgres(FakeConnection(rows))
    assert not result['rls_disabled']
    assert result['requires_review']
