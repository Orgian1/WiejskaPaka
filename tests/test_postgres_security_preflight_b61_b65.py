import pytest
from backend.postgres_security_preflight import inspect_security
from backend.neon_rls_preflight import SENSITIVE_TABLES


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows
    def fetchone(self):
        return self.rows[0] if self.rows else None
    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, role=None, tables=None):
        self.role = role or ('wiejskapaka_app', 'wp_test', False, False, False, False)
        self.tables = tables if tables is not None else [
            (name, True, True, False, True, True, True, False, 2)
            for name in SENSITIVE_TABLES
        ]
        self.queries = []
    def execute(self, sql, params=None):
        self.queries.append((sql, params))
        return FakeCursor([self.role] if params is None else self.tables)


def test_b61_clean_metadata_still_not_production_approval():
    con = FakeConnection()
    report = inspect_security(con)
    assert not report['findings']
    assert report['ready_for_production'] is False
    assert len(report['tables']) == len(SENSITIVE_TABLES)


def test_b62_detect_privileged_role():
    con = FakeConnection(role=('app', 'wp_test', True, True, True, False))
    report = inspect_security(con)
    assert any('ominąć RLS' in f for f in report['findings'])
    assert any('administracyjne' in f for f in report['findings'])


def test_b63_detect_missing_disabled_and_policyless():
    con = FakeConnection(tables=[
        (SENSITIVE_TABLES[0], False, False, False, True, True, True, True, 0),
        (SENSITIVE_TABLES[1], True, True, False, True, True, True, True, 0),
    ])
    report = inspect_security(con)
    assert any('RLS wyłączone' in f for f in report['findings'])
    assert any('RLS bez polityk' in f for f in report['findings'])
    assert report['tables'][SENSITIVE_TABLES[2]] == {'status': 'missing'}


def test_b64_owner_bypass_detected():
    con = FakeConnection(tables=[
        (name, True, False, True, True, True, True, True, 1)
        for name in SENSITIVE_TABLES
    ])
    report = inspect_security(con)
    assert sum('Właściciel tabeli' in f for f in report['findings']) == len(SENSITIVE_TABLES)


def test_b65_only_parameterized_selects_and_no_data_rows():
    con = FakeConnection()
    report = inspect_security(con)
    assert len(con.queries) == 2
    assert all(sql.lstrip().upper().startswith('SELECT') for sql, _ in con.queries)
    assert con.queries[1][1] == ('public', list(SENSITIVE_TABLES))
    assert 'password' not in str(report).lower()
