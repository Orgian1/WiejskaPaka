from backend.neon_permissions import audit_permissions, SENSITIVE_TABLES


class FakeCursor:
    def __init__(self, role_exists=True, rls=False):
        self.role_exists = role_exists
        self.rls = rls
        self.sql = ''
        self.params = ()

    def execute(self, sql, params=()):
        self.sql, self.params = sql, params

    def fetchone(self):
        if 'FROM pg_roles' in self.sql:
            return (True, False, False, False, False) if self.role_exists else None
        return (False,) if 'has_schema_privilege' in self.sql else (True,)

    def fetchall(self):
        return [(table, self.rls) for table in SENSITIVE_TABLES]

    def __enter__(self): return self
    def __exit__(self, *_): return False


class FakeConnection:
    def __init__(self, **kwargs): self.kwargs = kwargs
    def cursor(self): return FakeCursor(**self.kwargs)


def test_reports_sensitive_tables_without_rls():
    result = audit_permissions(FakeConnection())
    assert result['role_exists']
    assert result['safe_admin_flags']
    assert result['tables_without_rls_with_select'] == sorted(SENSITIVE_TABLES)
    assert result['production_ready'] is False


def test_missing_role():
    result = audit_permissions(FakeConnection(role_exists=False))
    assert not result['role_exists']
    assert not result['production_ready']


def test_rls_presence_does_not_certify_production():
    result = audit_permissions(FakeConnection(rls=True))
    assert result['tables_without_rls_with_select'] == []
    assert result['production_ready'] is False
