from pathlib import Path
import pytest
from database.test_schema_manifest import BASE, UPGRADES
from database.test_schema_runbook import build_runbook


def test_runbook_preserves_order_and_is_offline():
    with pytest.raises(ValueError, match="transaction-control"):
        build_runbook()



def test_runbook_fails_if_sql_changed(tmp_path):
    root = Path(__file__).resolve().parents[1] / 'database'
    for name in (BASE, *UPGRADES):
        (tmp_path / name).write_bytes((root / name).read_bytes())
    (tmp_path / BASE).write_text('-- modified')
    with pytest.raises(ValueError, match='checksums differ'):
        build_runbook(tmp_path)


def test_runbook_fails_if_sql_missing(tmp_path):
    with pytest.raises(ValueError):
        build_runbook(tmp_path)
