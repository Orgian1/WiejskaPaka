from pathlib import Path
from backend.neon_sql_inventory import inventory_file, project_inventory, summary


def test_inventory_detects_sensitive_read_write_and_dynamic(tmp_path):
    file = tmp_path / 'sample.py'
    file.write_text('''def f(con, sql):
    con.execute("SELECT * FROM orders JOIN users ON users.id=orders.buyer_id")
    con.execute("UPDATE orders SET status=? WHERE id=?", ("ok", 1))
    con.execute(sql)
''')
    rows = inventory_file(file)
    assert rows[0]['tables'] == ['orders', 'users']
    assert rows[1]['operation'] == 'WRITE'
    assert rows[2]['operation'] == 'DYNAMIC'


def test_project_scan_is_offline_and_flags_sensitive_tables():
    root = Path(__file__).resolve().parents[1]
    result = summary(project_inventory(root))
    assert 'orders' in result['sensitive']
    assert 'sessions' in result['sensitive']
    assert result['limitations']
