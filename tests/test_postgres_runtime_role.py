import pytest
from backend.postgres_runtime_role import assert_runtime_role

class Connection:
    def __init__(self,row):self.row=row
    def execute(self,sql):
        assert "pg_has_role" in sql and "rolreplication" in sql
        assert "has_schema_privilege" in sql
        assert "pg_read_all_data" in sql and "pg_execute_server_program" in sql
        return self
    def fetchone(self):return self.row

@pytest.mark.parametrize('row', [(True,False,False),(False,True,False),(False,False,True),
    (None,False,False),(0,False,False),None,(),{'elevated':False,'owns_relations':True,'can_create':False}])
def test_runtime_rejects_elevated_ownership_and_ambiguous_results(row):
    with pytest.raises(RuntimeError,match='konto aplikacyjne'):
        assert_runtime_role(Connection(row))

def test_runtime_accepts_separate_role():
    assert_runtime_role(Connection({'elevated':False,'owns_relations':False,'can_create':False}))
