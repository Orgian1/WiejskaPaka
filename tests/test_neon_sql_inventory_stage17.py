from backend.neon_sql_inventory import inventory_file, project_inventory, summary


def test_dynamic_fstring_reports_visible_sensitive_table(tmp_path):
    path = tmp_path / 'query.py'
    path.write_text('def run(con, column):\n    con.execute(f"SELECT {column} FROM order_locations")\n')
    result = inventory_file(path)[0]
    assert result['operation'] == 'DYNAMIC'
    assert result['tables'] == ['order_locations']
    assert result['requires_manual_review']


def test_dynamic_concat_keeps_known_table(tmp_path):
    path = tmp_path / 'query.py'
    path.write_text('def run(con, suffix):\n    con.execute("SELECT * FROM sessions " + suffix)\n')
    result = inventory_file(path)[0]
    assert result['operation'] == 'DYNAMIC'
    assert 'sessions' in result['tables']


def test_project_inventory_is_stable_and_non_mutating(tmp_path):
    backend = tmp_path / 'backend'
    backend.mkdir()
    (backend / 'a.py').write_text('def run(con):\n    con.execute("SELECT * FROM users")\n')
    report = project_inventory(tmp_path)
    assert report['a.py'][0]['tables'] == ['users']
    assert summary(report)['dynamic_queries'] == 0
